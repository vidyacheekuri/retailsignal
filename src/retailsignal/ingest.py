"""Download and normalize the UCI source without silently discarding revenue."""
from __future__ import annotations

import hashlib
import json
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

SOURCE_URL = "https://archive.ics.uci.edu/static/public/352/online%2Bretail.zip"
SOURCE_COLUMNS = ["InvoiceNo", "StockCode", "Description", "Quantity", "InvoiceDate",
                  "UnitPrice", "CustomerID", "Country"]


def download(root: Path) -> Path:
    raw = root / "data/raw"
    raw.mkdir(parents=True, exist_ok=True)
    target = raw / "Online Retail.xlsx"
    if target.exists():
        return target
    archive = raw / "online-retail.zip"
    if not archive.exists():
        temporary = archive.with_suffix(".partial")
        with urllib.request.urlopen(SOURCE_URL, timeout=120) as response:
            with temporary.open("wb") as out:
                while chunk := response.read(1024 * 1024):
                    out.write(chunk)
        temporary.replace(archive)
    with zipfile.ZipFile(archive) as z:
        # Extract only the known member, never arbitrary paths from the archive.
        target.write_bytes(z.read("Online Retail.xlsx"))
    return target


def clean(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    missing = set(SOURCE_COLUMNS) - set(raw.columns)
    if missing:
        raise ValueError(f"Missing source columns: {sorted(missing)}")
    original = raw[SOURCE_COLUMNS].copy()
    duplicate = original.duplicated(keep="first")
    d = original.rename(columns=dict(zip(SOURCE_COLUMNS, [
        "invoice_id", "product_id", "description", "quantity", "invoice_at",
        "unit_price", "customer_id", "country"])))
    d["source_row"] = np.arange(2, len(d) + 2)
    for col in ["invoice_id", "product_id", "country"]:
        d[col] = d[col].astype("string").str.strip().replace("", pd.NA)
    d["invoice_at"] = pd.to_datetime(d["invoice_at"], errors="coerce")
    d["quantity"] = pd.to_numeric(d["quantity"], errors="coerce")
    d["unit_price"] = pd.to_numeric(d["unit_price"], errors="coerce")
    customer = pd.to_numeric(d["customer_id"], errors="coerce")
    invalid_customer = customer.notna() & ((customer % 1 != 0) | (customer <= 0))
    d["customer_id"] = customer.mask(invalid_customer).astype("Int64").astype("string")
    cancel = d["invoice_id"].str.upper().str.startswith("C").fillna(False)
    invalid = (d[["invoice_id", "product_id", "country", "invoice_at", "quantity", "unit_price"]]
               .isna().any(axis=1) | ~np.isfinite(d["quantity"]) | ~np.isfinite(d["unit_price"])
               | (d["quantity"] == 0) | (d["unit_price"] <= 0)
               | (d["quantity"] % 1 != 0) | (cancel & (d["quantity"] > 0)))
    d["rejection_reason"] = np.select([duplicate, invalid], ["exact_duplicate", "invalid_transaction"], default="")
    rejected = d.loc[duplicate | invalid].copy()
    accepted = d.loc[~(duplicate | invalid)].drop(columns="rejection_reason").copy()
    accepted["description"] = accepted["description"].fillna("Unknown product").astype(str)
    accepted["is_credit"] = accepted["quantity"] < 0
    # Integer pennies prevent floating point drift in financial reconciliation.
    accepted["unit_price_pence"] = (accepted["unit_price"] * 100).round().astype("int64")
    accepted["net_pence"] = accepted["quantity"].astype("int64") * accepted["unit_price_pence"]
    accepted["gross_pence"] = accepted["net_pence"].clip(lower=0)
    accepted["credit_pence"] = -accepted["net_pence"].clip(upper=0)
    accepted["invoice_date"] = accepted["invoice_at"].dt.date
    quality = {
        "source_rows": len(original), "accepted_rows": len(accepted),
        "rejected_rows": len(rejected), "exact_duplicates": int(duplicate.sum()),
        "invalid_transactions_excluding_duplicates": int((invalid & ~duplicate).sum()),
        "accepted_missing_customer": int(accepted["customer_id"].isna().sum()),
        "invalid_customer_ids": int(invalid_customer.sum()),
        "subpenny_price_rows": int(((accepted.unit_price * 100 - accepted.unit_price_pence).abs() > 1e-6).sum()),
        "rounding_net_difference_gbp": float((accepted.net_pence / 100 - accepted.quantity * accepted.unit_price).sum()),
        "min_timestamp": str(accepted.invoice_at.min()), "max_timestamp": str(accepted.invoice_at.max()),
        "gross_gbp": int(accepted.gross_pence.sum()) / 100,
        "credits_gbp": int(accepted.credit_pence.sum()) / 100,
        "net_gbp": int(accepted.net_pence.sum()) / 100,
    }
    assert quality["source_rows"] == quality["accepted_rows"] + quality["rejected_rows"]
    assert (accepted.gross_pence - accepted.credit_pence == accepted.net_pence).all()
    return accepted, rejected, quality


def ingest(root: Path, source: Path) -> tuple[pd.DataFrame, dict]:
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    stage = root / "data/staging"
    stage.mkdir(parents=True, exist_ok=True)
    cache = stage / f"{digest}.parquet"
    if cache.exists():
        raw = pd.read_parquet(cache)
    else:
        raw = pd.read_excel(source, dtype={"InvoiceNo": "string", "StockCode": "string",
                                           "Description": "string", "Country": "string"})
        raw.to_parquet(cache, index=False)
    accepted, rejected, quality = clean(raw)
    rejected.to_parquet(stage / "quarantine.parquet", index=False)
    quality.update({"source_url": SOURCE_URL, "sha256": digest, "pipeline_version": "1.0.0"})
    (root / "reports").mkdir(exist_ok=True)
    (root / "reports/data_quality.json").write_text(json.dumps(quality, indent=2))
    return accepted, quality
