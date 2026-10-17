-- Run against data/warehouse.duckdb after the full build.

-- 1. Revenue concentration: window function over aggregated market results.
WITH markets AS (
  SELECT country, SUM(net_pence)/100.0 AS net_revenue
  FROM fact_sales GROUP BY country
)
SELECT country, net_revenue,
       net_revenue / SUM(net_revenue) OVER () AS net_revenue_share,
       DENSE_RANK() OVER (ORDER BY net_revenue DESC) AS revenue_rank
FROM markets ORDER BY revenue_rank;

-- 2. Complete-month growth. Never compare partial December to November.
WITH complete AS (
  SELECT month, net_revenue, LAG(net_revenue) OVER (ORDER BY month) AS previous_net
  FROM mart_monthly WHERE NOT partial_month
)
SELECT *, (net_revenue - previous_net)/NULLIF(previous_net,0) AS net_growth
FROM complete ORDER BY month;

-- 3. Products worth reviewing for unusually large credit burdens.
SELECT product_id, description, gross_revenue, credits, net_revenue,
       credits / NULLIF(gross_revenue,0) AS credit_ratio
FROM mart_products WHERE gross_revenue >= 10000
ORDER BY credits DESC LIMIT 20;

-- 4. Identity coverage by month (do not sum daily distinct customers).
SELECT strftime(invoice_date, '%Y-%m') AS month,
       COUNT(DISTINCT customer_id) AS known_customers,
       SUM(CASE WHEN customer_id IS NULL THEN gross_pence ELSE 0 END)::DOUBLE
           / NULLIF(SUM(gross_pence),0) AS anonymous_gross_share
FROM fact_sales GROUP BY month ORDER BY month;
