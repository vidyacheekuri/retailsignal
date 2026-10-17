# Data dictionary and metric contracts

## Source and cleaning

Source: UCI Online Retail, December 1, 2010 to December 9, 2011. Original columns: InvoiceNo, StockCode, Description, Quantity, InvoiceDate, UnitPrice, CustomerID, Country. Currency: GBP. No timestamp timezone is supplied; analysis treats the source timestamps as naive local business time without inventing a conversion.

Exact duplicate source rows are quarantined after the first occurrence. This is an analytical assumption: an identical line could be intentional. Quarantine preserves the source row and rejection reason for audit. Invalid transactions are missing invoice/product/country/date/quantity/price, non-finite quantity/price, zero or fractional quantity, non-positive unit price, or a cancellation invoice with positive quantity. Free goods and administrative stock adjustments without valid price are excluded from the financial proxy.

Missing customer IDs remain in accounting. Malformed numeric customer IDs are treated as unidentified, and counted separately. Product descriptions are descriptive labels, not join keys. A representative description is chosen for each product; changing descriptions do not create new products.

## Ledger

| Column | Meaning |
|---|---|
| source_row | Original Excel row number, including the header offset |
| invoice_id | Invoice identifier, including credit prefixes |
| product_id | String stock code, including administrative codes |
| invoice_at / invoice_date | Timestamp / calendar date |
| customer_id | Nullable pseudonymous source identifier |
| quantity | Signed integral quantity |
| unit_price_pence | Unit price rounded to integer pennies |
| gross_pence | Positive line amount, otherwise zero |
| credit_pence | Absolute negative line amount, otherwise zero |
| net_pence | Gross minus credit pennies |
| is_credit | Negative quantity; a ledger credit, not a matched return |

## Business KPIs

| Metric | Definition | Caveat |
|---|---|---|
| Gross revenue | Sum of positive accepted line amounts | Includes administrative codes with valid amounts |
| Credits | Absolute sum of negative accepted line amounts | Includes cancellations and adjustments |
| Net revenue | Gross revenue minus credits | Recorded ledger proxy, not audited accounting revenue or profit |
| Credit ratio | Credits / gross revenue | Can exceed 100% in a selected slice because original sales may lie outside it |
| Sales orders | Distinct positive-sale invoices | Daily-country counts are additive only when invoices belong to one date and country |
| Average order value | Gross revenue / sales orders | Uses positive sales, not credits |
| Identified revenue share | 1 − anonymous gross / total gross | Revenue coverage, not percentage of unique people |
| Cohort retention | Active known customers / original known cohort size | Positive purchases only; complete months; no causal interpretation |
| Mean repeat propensity | Mean model probability in selected snapshot audience | Not expected incremental campaign conversion |

`known_customers` in daily marts is **not additive across dates**. It is hidden in the Power BI fact and never summed into a unique-customer KPI.

## Model features

Each row represents one identified customer with at least one accepted positive purchase in `[as_of − 180 days, as_of)`. Credits and purchases at or after the cutoff never enter features.

| Feature | Definition |
|---|---|
| recency_days | Fractional days since latest purchase |
| orders_180d | Distinct purchase invoices in the lookback |
| gross_180d | Positive accepted amounts in GBP |
| aov_180d | Gross / order count |
| products_180d | Distinct product codes purchased |
| active_days_180d | Distinct purchase dates |
| tenure_days | Days since earliest purchase **in the 180-day lookback**, not true customer lifetime |
| orders_30d | Distinct purchase invoices in the last 30 days |
| credits_180d | Absolute credits in GBP within the lookback |
| credit_ratio | Lookback credits / lookback gross; zero fallback if nominal sub-penny pricing rounds gross to zero |

Label `repeat_30d = 1` when the customer has a positive purchase in `[as_of, as_of + 30 days)`. It is a future behavior label, not churn, campaign response, or customer lifetime value.

The latest scoring date is December 10, 2011, but source observation ends midday December 9. It is a historical batch illustration, not a current customer list. Outcomes after that date are not present.
