"""Point-in-time features: never consume transactions at or after the cutoff."""
import numpy as np
import pandas as pd

FEATURES = ["recency_days", "orders_180d", "gross_180d", "aov_180d", "products_180d",
            "active_days_180d", "tenure_days", "orders_30d", "credits_180d", "credit_ratio"]


def snapshot(transactions: pd.DataFrame, as_of: str, with_labels: bool = True,
             observation_end: str | None = None) -> pd.DataFrame:
    cutoff = pd.Timestamp(as_of)
    end = cutoff + pd.Timedelta(days=30)
    if with_labels:
        observed = pd.Timestamp(observation_end) if observation_end else transactions.invoice_at.max()
        if observed < end:
            raise ValueError("Incomplete 30-day label window")
    history = transactions.loc[(transactions.invoice_at < cutoff)
                               & (transactions.invoice_at >= cutoff - pd.Timedelta(days=180))
                               & transactions.customer_id.notna()]
    sales = history.loc[~history.is_credit]
    if sales.empty:
        return pd.DataFrame(columns=["customer_id", *FEATURES, "as_of"])
    f = sales.groupby("customer_id").agg(
        last_purchase=("invoice_at", "max"), first_purchase=("invoice_at", "min"),
        orders_180d=("invoice_id", "nunique"), gross_180d=("gross_pence", "sum"),
        products_180d=("product_id", "nunique"), active_days_180d=("invoice_date", "nunique"))
    f["gross_180d"] /= 100
    f["recency_days"] = (cutoff - f.last_purchase).dt.total_seconds() / 86400
    f["tenure_days"] = (cutoff - f.first_purchase).dt.total_seconds() / 86400
    f["aov_180d"] = f.gross_180d / f.orders_180d
    recent = sales.loc[sales.invoice_at >= cutoff - pd.Timedelta(days=30)]
    f["orders_30d"] = recent.groupby("customer_id").invoice_id.nunique().reindex(f.index, fill_value=0)
    f["credits_180d"] = history.groupby("customer_id").credit_pence.sum().reindex(f.index, fill_value=0) / 100
    # Nominal sub-penny prices can round to zero. Keep the record and use a
    # documented zero fallback rather than passing infinity into the estimator.
    f["credit_ratio"] = (f.credits_180d / f.gross_180d.replace(0, np.nan)).fillna(0)
    f["as_of"] = cutoff.strftime("%Y-%m-%d")
    if with_labels:
        future = transactions.loc[(transactions.invoice_at >= cutoff) & (transactions.invoice_at < end)
                                  & ~transactions.is_credit & transactions.customer_id.notna()]
        f["repeat_30d"] = f.index.isin(future.customer_id).astype(int)
    f["segment"] = np.select([
        (f.recency_days <= 30) & (f.orders_180d >= 4),
        (f.recency_days <= 30) & (f.orders_180d < 4),
        (f.recency_days > 60) & (f.orders_180d >= 3),
        f.recency_days > 90], ["Champions", "Recent shoppers", "Lapsing loyal", "Dormant"], default="Developing")
    return f.drop(columns=["last_purchase", "first_purchase"]).reset_index()
