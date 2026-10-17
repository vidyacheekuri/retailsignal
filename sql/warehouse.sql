-- Grain: one accepted source invoice line. Credits are independent events,
-- not matched returns; we do not fabricate links to original purchases.
CREATE OR REPLACE TABLE fact_sales AS SELECT * FROM accepted;
CREATE OR REPLACE TABLE dim_date AS
SELECT CAST(day AS DATE) AS date_key, year(day) AS year,
       month(day) AS month_number, strftime(day, '%Y-%m') AS month,
       strftime(day, '%A') AS weekday
FROM generate_series((SELECT min(invoice_date) FROM fact_sales),
                     (SELECT max(invoice_date) FROM fact_sales), INTERVAL 1 DAY) AS t(day);
CREATE OR REPLACE TABLE dim_country AS
SELECT DISTINCT country FROM fact_sales;
CREATE OR REPLACE TABLE mart_daily_country AS
SELECT invoice_date AS date_key, country,
       sum(gross_pence)/100.0 AS gross_revenue,
       sum(credit_pence)/100.0 AS credits,
       sum(net_pence)/100.0 AS net_revenue,
       count(DISTINCT CASE WHEN NOT is_credit THEN invoice_id END) AS orders,
       count(DISTINCT customer_id) AS known_customers,
       sum(CASE WHEN customer_id IS NULL THEN gross_pence ELSE 0 END)/100.0 AS anonymous_gross,
       count(*) AS line_count
FROM fact_sales GROUP BY ALL;
CREATE OR REPLACE TABLE mart_monthly AS
SELECT strftime(date_key, '%Y-%m') AS month,
       sum(gross_revenue) AS gross_revenue, sum(credits) AS credits,
       sum(net_revenue) AS net_revenue, sum(orders) AS orders,
       sum(credits)/nullif(sum(gross_revenue),0) AS credit_ratio,
       sum(gross_revenue)/nullif(sum(orders),0) AS average_order_value,
       date_trunc('month', max(date_key)) = date_trunc('month', (SELECT max(invoice_date) FROM fact_sales))
           AND (SELECT max(invoice_date) FROM fact_sales) < last_day(max(date_key)) AS partial_month
FROM mart_daily_country GROUP BY month ORDER BY month;
CREATE OR REPLACE TABLE mart_products AS
SELECT product_id, min(description) AS description,
       sum(gross_pence)/100.0 AS gross_revenue,
       sum(credit_pence)/100.0 AS credits, sum(net_pence)/100.0 AS net_revenue,
       sum(CASE WHEN NOT is_credit THEN quantity ELSE 0 END) AS units_sold,
       count(DISTINCT CASE WHEN NOT is_credit THEN invoice_id END) AS orders
FROM fact_sales GROUP BY product_id;
-- Denominator fixed at the original cohort size; incomplete calendar months
-- never appear as retention observations.
CREATE OR REPLACE TABLE mart_cohorts AS
WITH purchases AS (
 SELECT DISTINCT customer_id, date_trunc('month', invoice_at)::DATE AS activity_month
 FROM fact_sales WHERE NOT is_credit AND customer_id IS NOT NULL
), first_purchase AS (
 SELECT customer_id, min(activity_month) AS cohort_month FROM purchases GROUP BY customer_id
), sizes AS (
 SELECT cohort_month, count(*) AS cohort_size FROM first_purchase GROUP BY cohort_month
), complete_months AS (
 SELECT DISTINCT date_trunc('month', date_key)::DATE AS month FROM dim_date
 WHERE last_day(date_key) < (SELECT max(invoice_date) FROM fact_sales)
), grid AS (
 SELECT s.cohort_month, m.month AS activity_month, s.cohort_size
 FROM sizes s JOIN complete_months m ON m.month >= s.cohort_month
), active AS (
 SELECT f.cohort_month, p.activity_month, count(*) AS active_customers
 FROM purchases p JOIN first_purchase f USING (customer_id) GROUP BY ALL
)
SELECT strftime(g.cohort_month, '%Y-%m') AS cohort,
       date_diff('month', g.cohort_month, g.activity_month) AS month_index,
       g.cohort_size, coalesce(a.active_customers, 0) AS active_customers,
       coalesce(a.active_customers, 0)::DOUBLE / g.cohort_size AS retention
FROM grid g LEFT JOIN active a USING (cohort_month, activity_month)
ORDER BY cohort, month_index;
