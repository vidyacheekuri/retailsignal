from pathlib import Path
import json
import duckdb
import numpy as np
import pandas as pd
import pytest
from retailsignal.ingest import clean, SOURCE_COLUMNS
from retailsignal.features import snapshot, FEATURES
from retailsignal.model import evaluate, validate_features
from retailsignal.warehouse import build_warehouse

ROOT = Path(__file__).resolve().parents[1]


def raw(rows):
    return pd.DataFrame(rows, columns=SOURCE_COLUMNS)


def sample():
    return raw([
        ["100", "P1", "Cup", 2, "2011-01-01", 5, 10, "UK"],
        ["101", "P1", "Cup", 1, "2011-01-15", 5, None, "UK"],
        ["C102", "P1", "Cup", -1, "2011-02-01", 5, 10, "UK"],
        ["103", "P2", "Plate", 1, "2011-03-01", 8, 10, "UK"],
        ["104", "P1", "Cup", 1, "2011-03-05", 5, 20, "UK"],
        ["105", "P1", "Cup", 1, "2011-05-01", 5, 20, "UK"],
    ])


def test_clean_reconciles_credits_anonymous_and_duplicates():
    source = pd.concat([sample(), sample().iloc[[0]]], ignore_index=True)
    accepted, rejected, q = clean(source)
    assert len(accepted) == 6 and len(rejected) == 1
    assert q["gross_gbp"] == 33 and q["credits_gbp"] == 5 and q["net_gbp"] == 28
    assert accepted.customer_id.isna().sum() == 1
    assert rejected.rejection_reason.iloc[0] == "exact_duplicate"
    assert q["source_rows"] == q["accepted_rows"] + q["rejected_rows"]


@pytest.mark.parametrize("column,value", [("Quantity",0),("Quantity",1.5),("UnitPrice",-2),
    ("UnitPrice",float("inf")),("InvoiceDate","bad-date"),("InvoiceNo",None),("Country","")])
def test_invalid_records_are_quarantined(column,value):
    source = sample().iloc[[0]].copy()
    source[column] = value
    accepted, rejected, _ = clean(source)
    assert accepted.empty and len(rejected) == 1


def test_positive_cancellation_is_not_counted_as_sale():
    source = sample().iloc[[0]].copy()
    source["InvoiceNo"] = "C100"
    assert clean(source)[0].empty


def test_features_cannot_see_future():
    data = clean(sample())[0]
    before = snapshot(data, "2011-03-01", observation_end="2011-05-01")
    changed = data.copy()
    future = changed.invoice_at >= pd.Timestamp("2011-03-01")
    changed.loc[future, "gross_pence"] = 99999999
    after = snapshot(changed, "2011-03-01", observation_end="2011-05-01")
    pd.testing.assert_frame_equal(before[FEATURES], after[FEATURES])
    assert before.customer_id.tolist() == ["10"]
    assert before.repeat_30d.tolist() == [1]
    assert before.orders_180d.tolist() == [1]
    assert before.gross_180d.tolist() == [10]


def test_label_window_is_half_open():
    source = sample()
    source.loc[source.InvoiceNo == "103", "InvoiceDate"] = "2011-03-31"
    frame = snapshot(clean(source)[0], "2011-03-01", observation_end="2011-05-01")
    assert frame.repeat_30d.tolist() == [0]  # Exactly day 30 is outside the window.


def test_incomplete_future_window_fails():
    with pytest.raises(ValueError, match="Incomplete"):
        snapshot(clean(sample())[0], "2011-05-01")


def test_warehouse_idempotence_and_missing_cohort_months(tmp_path):
    (tmp_path / "sql").mkdir()
    (tmp_path / "data").mkdir()
    (tmp_path / "sql/warehouse.sql").write_text((ROOT / "sql/warehouse.sql").read_text())
    data = clean(sample())[0]
    build_warehouse(tmp_path,data)
    first = (tmp_path / "data/exports/mart_daily_country.csv").read_bytes()
    build_warehouse(tmp_path,data)
    assert first == (tmp_path / "data/exports/mart_daily_country.csv").read_bytes()
    with duckdb.connect(str(tmp_path / "data/warehouse.duckdb")) as con:
        assert con.execute("SELECT sum(net_pence) FROM fact_sales").fetchone()[0] == 2800
        row = con.execute("SELECT retention FROM mart_cohorts WHERE cohort='2011-01' AND month_index=1").fetchone()
        assert row == (0.0,)
        assert con.execute("SELECT max(month_index) FROM mart_cohorts WHERE cohort='2011-01'").fetchone()[0] == 3


def test_scoring_contract_rejects_leaky_or_invalid_inputs():
    with pytest.raises(ValueError, match="Missing features"):
        validate_features(pd.DataFrame({"customer_id":[1]}))
    features = snapshot(clean(sample())[0], "2011-03-01", with_labels=False)
    features.loc[0,"orders_30d"] = 100
    with pytest.raises(ValueError, match="order counts"):
        validate_features(features)


def test_capacity_metrics():
    m = evaluate([1,0,1,0,0], [.9,.2,.8,.1,.3])
    assert m["precision_at_20pct"] == 1
    assert m["capture_at_20pct"] == .5
    assert m["lift_at_20pct"] == 2.5


def test_nominal_prices_do_not_create_infinite_features():
    source = sample().iloc[[0]].copy()
    source["UnitPrice"] = .001
    features = snapshot(clean(source)[0], "2011-03-01", with_labels=False)
    assert features.gross_180d.iloc[0] == 0
    assert features.credit_ratio.iloc[0] == 0
    assert np.isfinite(validate_features(features)).all().all()


def test_published_artifacts_reconcile():
    q = json.loads((ROOT / "reports/data_quality.json").read_text())
    daily = pd.read_csv(ROOT / "data/exports/mart_daily_country.csv")
    assert np.isclose(daily.net_revenue.sum(), q["net_gbp"], atol=.01)
    assert np.allclose(daily.gross_revenue - daily.credits, daily.net_revenue, atol=.0001)
    cohorts = pd.read_csv(ROOT / "data/exports/mart_cohorts.csv")
    assert cohorts.retention.between(0,1).all()
    assert (cohorts[cohorts.month_index == 0].retention == 1).all()
    assert "2011-12" not in cohorts.cohort.tolist()
    scores = pd.read_csv(ROOT / "data/exports/customer_scores.csv")
    assert scores.customer_id.is_unique
    assert scores.repeat_probability.between(0,1).all()
    assert np.isfinite(validate_features(scores)).all().all()
    predictions = pd.read_csv(ROOT / "data/exports/test_predictions.csv")
    model = json.loads((ROOT / "reports/model_evaluation.json").read_text())
    assert evaluate(predictions.repeat_30d,predictions.repeat_probability)["average_precision"] == pytest.approx(model["test"]["average_precision"])
