from pathlib import Path
import duckdb
import pandas as pd

EXPORTS = ["dim_date", "dim_country", "mart_daily_country", "mart_monthly", "mart_products", "mart_cohorts"]


def build_warehouse(root: Path, accepted: pd.DataFrame) -> None:
    exports = root / "data/exports"
    exports.mkdir(parents=True, exist_ok=True)
    # A transaction makes table replacement all-or-nothing on SQL failures.
    with duckdb.connect(str(root / "data/warehouse.duckdb")) as con:
        con.register("accepted", accepted)
        con.execute("BEGIN")
        try:
            con.execute((root / "sql/warehouse.sql").read_text())
            counts = con.execute("SELECT count(*), sum(net_pence) FROM fact_sales").fetchone()
            if counts != (len(accepted), int(accepted.net_pence.sum())):
                raise ValueError("Warehouse/source reconciliation failed")
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise
        for table in EXPORTS:
            frame = con.execute(f"SELECT * FROM {table} ORDER BY ALL").df()
            frame.to_csv(exports / f"{table}.csv", index=False, float_format="%.6f")
