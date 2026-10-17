"""Temporal model selection, honest holdout evaluation, and batch inference."""
from __future__ import annotations

import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .features import FEATURES, snapshot
from .monitoring import drift_report

SEED = 42
TRAIN_DATES = ["2011-04-01", "2011-05-01", "2011-06-01"]
VALIDATION_DATE = "2011-08-01"
TEST_DATE = "2011-10-01"
SCORE_DATE = "2011-12-10"


def evaluate(y, probability) -> dict:
    y, probability = np.asarray(y), np.asarray(probability)
    k = max(1, int(np.ceil(len(y) * .2)))
    top = np.argsort(-probability, kind="stable")[:k]
    precision = float(y[top].mean())
    rate = float(y.mean())
    return {"customers": len(y), "positive_rate": rate,
            "average_precision": float(average_precision_score(y, probability)),
            "roc_auc": float(roc_auc_score(y, probability)),
            "brier_score": float(brier_score_loss(y, probability)),
            "precision_at_20pct": precision, "lift_at_20pct": precision / rate,
            "capture_at_20pct": float(y[top].sum() / y.sum())}


def validate_features(frame: pd.DataFrame) -> pd.DataFrame:
    missing = set(FEATURES) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing features: {sorted(missing)}")
    x = frame[FEATURES].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(x.to_numpy()).all() or (x < 0).any().any():
        raise ValueError("Features must be finite, non-negative numeric values")
    if (x.orders_180d < 1).any() or (x.orders_30d > x.orders_180d).any():
        raise ValueError("Invalid historical order counts")
    return x


def batch_score(model_path: Path, input_path: Path, output_path: Path) -> None:
    # Only load locally trained, trusted joblib artifacts (pickle is executable).
    bundle = joblib.load(model_path)
    if bundle["features"] != FEATURES:
        raise ValueError("Model feature contract mismatch")
    frame = pd.read_csv(input_path)
    frame["repeat_probability"] = bundle["model"].predict_proba(validate_features(frame))[:, 1]
    frame.to_csv(output_path, index=False)


def train(root: Path, transactions: pd.DataFrame) -> dict:
    train_data = pd.concat([snapshot(transactions, d) for d in TRAIN_DATES], ignore_index=True)
    validation = snapshot(transactions, VALIDATION_DATE)
    test = snapshot(transactions, TEST_DATE)
    candidates = {
        "Logistic regression": make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, C=.3, random_state=SEED)),
        "Gradient boosting": HistGradientBoostingClassifier(max_iter=150, max_leaf_nodes=15,
                         l2_regularization=10, learning_rate=.05, random_state=SEED),
    }
    comparisons = []
    for name, estimator in candidates.items():
        estimator.fit(train_data[FEATURES], train_data.repeat_30d)
        comparisons.append({"model": name, "split": "validation", **evaluate(
            validation.repeat_30d, estimator.predict_proba(validation[FEATURES])[:, 1])})
    # Choose once by validation AP, then refit on train + validation before testing.
    winner = max(comparisons, key=lambda row: row["average_precision"])["model"]
    final = clone(candidates[winner])
    development = pd.concat([train_data, validation], ignore_index=True)
    final.fit(development[FEATURES], development.repeat_30d)
    predictions = final.predict_proba(test[FEATURES])[:, 1]
    metrics = evaluate(test.repeat_30d, predictions)
    comparisons.append({"model": winner, "split": "test", **metrics})
    # A simple hand-built recency baseline provides a meaningful ranking comparison.
    recency_probability = np.exp(-test.recency_days.to_numpy() / 45)
    comparisons.append({"model": "Recency heuristic", "split": "test", **evaluate(test.repeat_30d, recency_probability)})
    constant = np.full(len(test), development.repeat_30d.mean())
    comparisons.append({"model": "Constant rate", "split": "test", **evaluate(test.repeat_30d, constant)})
    rng = np.random.default_rng(SEED)
    aps = []
    for _ in range(500):
        indices = rng.integers(0, len(test), len(test))
        y = test.repeat_30d.to_numpy()[indices]
        if len(np.unique(y)) > 1:
            aps.append(average_precision_score(y, predictions[indices]))
    importance = permutation_importance(final, test[FEATURES], test.repeat_30d,
                    scoring="average_precision", n_repeats=10, random_state=SEED, n_jobs=1)
    exports = root / "data/exports"
    pd.DataFrame({"feature": FEATURES, "importance": importance.importances_mean,
                  "std": importance.importances_std}).sort_values("importance", ascending=False).to_csv(
                      exports / "model_importance.csv", index=False)
    pd.DataFrame(comparisons).to_csv(exports / "model_metrics.csv", index=False)
    test["repeat_probability"] = predictions
    test[["customer_id", "repeat_30d", "repeat_probability", "segment"]].to_csv(exports / "test_predictions.csv", index=False)
    test["probability_band"] = pd.cut(test.repeat_probability, np.linspace(0, 1, 11), include_lowest=True)
    calibration = test.groupby("probability_band", observed=True).agg(
        predicted=("repeat_probability", "mean"), observed=("repeat_30d", "mean"), customers=("repeat_30d", "size"))
    calibration.reset_index().to_csv(exports / "model_calibration.csv", index=False)
    scores = snapshot(transactions, SCORE_DATE, with_labels=False)
    scores["repeat_probability"] = final.predict_proba(scores[FEATURES])[:, 1]
    scores["priority_rank"] = scores.repeat_probability.rank(method="first", ascending=False).astype(int)
    drift_report(development, scores, FEATURES).to_csv(exports / "feature_drift.csv", index=False)
    scores.sort_values("priority_rank").to_csv(exports / "customer_scores.csv", index=False, float_format="%.6f")
    segments = scores.groupby("segment").agg(customers=("customer_id", "size"),
        historical_gross=("gross_180d", "sum"), mean_repeat_probability=("repeat_probability", "mean"))
    segments.reset_index().to_csv(exports / "mart_segments.csv", index=False)
    models = root / "models"
    models.mkdir(exist_ok=True)
    joblib.dump({"model": final, "features": FEATURES, "version": "1.0.0", "seed": SEED}, models / "repeat_purchase.joblib")
    summary = {"selected_model": winner, "train_snapshots": TRAIN_DATES,
               "validation_date": VALIDATION_DATE, "test_date": TEST_DATE, "score_date": SCORE_DATE,
               "train_rows": len(train_data), "validation_customers": len(validation),
               "test": metrics, "test_ap_ci95": np.quantile(aps, [.025, .975]).tolist(),
               "recency_baseline_ap": comparisons[-2]["average_precision"],
               "scored_customers": len(scores), "seed": SEED}
    (root / "reports/model_evaluation.json").write_text(json.dumps(summary, indent=2))
    return summary
