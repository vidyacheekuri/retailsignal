# Architecture and design decisions

## Design goal

A hiring reviewer should be able to run the dashboard in minutes, inspect evidence without rebuilding, and reproduce the complete pipeline from the original source. Keep infrastructure small enough to understand while making the analytical decisions explicit.

## Layers and contracts

| Layer | Artifact | Grain / responsibility |
|---|---|---|
| Source | UCI workbook, local ZIP | Untouched source; SHA-256 fingerprint |
| Staging | Content-addressed Parquet | Typed source cache; quarantine with source row and reason |
| Warehouse | `fact_sales` in DuckDB | One accepted source invoice line |
| Dimensions | `dim_date`, `dim_country` | One date / country |
| Revenue mart | `mart_daily_country` | Date × country; additive money and orders |
| Cohort mart | `mart_cohorts` | First observed purchase month × elapsed month |
| Feature snapshots | In-memory customer frames | Customer × as-of date, 180-day history |
| Model artifact | Local joblib bundle | Estimator + feature contract + version |
| Serving | Versioned CSVs and Streamlit | Historical batch decision support |
| BI | PBIP + semantic model | CSV import; date/country revenue relationships |

## Why these choices?

**DuckDB and SQL:** reproducible local analytical joins and aggregates without a paid warehouse. The design transfers to a cloud warehouse, but this repository does not pretend to run Spark, Kafka, or cloud infrastructure.

**Batch scoring:** matches a periodic analyst review queue. A real-time API adds operational complexity without a demonstrated business requirement.

**Integer pennies:** avoids floating-point differences in money reconciliation. Four source rows contain sub-penny unit prices. The rounding effect is recorded in `reports/data_quality.json`.

**Separate analytical grains:** monthly retention and customer snapshots must not be joined directly to transaction lines. Such joins multiply records and inflate totals. They are separate Power BI fact-like tables; revenue filters are scoped to the revenue dashboard page.

**CSV marts in Git:** make the app usable immediately and allow reviewers to inspect data. The raw workbook, warehouse, executable model, and cache are excluded. Changes in derived results remain reviewable.

## Failure and rerun behavior

- Source download writes a partial file and renames it only on completion.
- Exact source member extraction avoids arbitrary ZIP paths.
- Workbook cache is keyed by its content fingerprint.
- Required columns fail fast; invalid rows receive auditable quarantine reasons.
- SQL table replacement runs inside a transaction and reconciles against accepted source rows and pennies.
- Repeated builds replace outputs; a test checks idempotent warehouse exports.
- CSV/model/report publication is sequential, not a transactional multi-file release. Do not rebuild while serving the dashboard in a production system; build into a versioned directory, validate, and atomically switch the active release.

## What production would still require

Recent operational data, agreed accounting treatment, source system ownership, orchestration, monitoring of failures and latency, access controls, retention policies, drift review with delayed outcome labels, and a controlled campaign experiment. Large-scale distributed processing and real-time serving are deliberately outside the demonstrated implementation.
