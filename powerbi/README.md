# Power BI project

This folder contains an editable **PBIP project**, not a screenshot or a renamed PBIX. It includes a TMSL semantic model, Power Query CSV imports, a folder parameter, DAX measures, and PBIR report definitions.

## Open and refresh on Windows

1. Clone or download the complete repository; keep its folders together.
2. Open `RetailSignal.pbip` in a current Windows Power BI Desktop version that supports PBIP/PBIR.
3. In Transform Data → Manage Parameters, change **DataFolder** from `C:/retailsignal/data/exports` to the absolute path of your repository's `data/exports` directory. Forward slashes work in the supplied M expressions.
4. Apply changes and refresh. All input CSVs are checked in; a full Python rebuild is optional.
5. If prompted, set local file source privacy appropriately for this public dataset.
6. Optionally import `RetailSignal.theme.json` through View → Themes → Browse for themes.
7. Inspect the three report pages and save the project. Save a PBIX copy in Desktop if you need a packaged file.

## Report pages

- **Revenue:** four KPI cards, revenue trend, country comparison, date and country slicers, identity coverage.
- **Retention:** cohort matrix, segment distribution, scoring-population card. All markets; complete calendar months only.
- **Propensity:** audience segment, scored count, mean propensity, customer queue. December 10 historical snapshot; sort `priority_rank` ascending.

## Model design

`Date` and `Country` each have a one-to-many, single-direction relationship to `DailyRevenue`. `Cohorts` and `Customers` are deliberately independent analytical grains. Date/country filters do not apply to the separate customer/cohort pages. The Date table spans every calendar date in the source and identifies `date_key` as its key.

`known_customers` is hidden because daily distinct counts are not additive. Cohort Retention returns blank when multiple elapsed months are in scope, avoiding a misleading matrix grand total. Source fields are typed in Power Query with `en-GB` culture. Measures are also listed in `measures.dax`.

The net month-over-month measure is provided for exploration, but December 2011 is partial. Do not use it as a like-for-like monthly performance claim without restricting to complete periods.

## Validation status

- 23 PBIR/report JSON files pass Microsoft's public JSON schemas.
- Automated tests verify CSV columns, model relationships, and every visual's referenced table/field.
- Python and SQL totals reconcile; all Streamlit pages execute.
- **Not yet validated:** Power BI Desktop opening, Power Query refresh, DAX execution, and visual rendering. These require Windows Power BI Desktop, unavailable on the macOS build host. Schema validation does not prove runtime correctness.

Expected all-data cards after refresh: **£9,748,131.07 net**, **£10,642,110.80 gross**, **8.4004% credit ratio (8.4% displayed)**, and **19,960 sales orders**. Use `data/exports/mart_daily_country.csv` for exact comparisons.

Recreate the source definitions with `python scripts/build_powerbi.py`. This resets the DataFolder default; commit any intentional Desktop changes before regenerating.

References: [Microsoft semantic model project format](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-dataset), [PBIR report format and schemas](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-report).
