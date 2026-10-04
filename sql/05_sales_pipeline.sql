-- 05_sales_pipeline.sql
-- Question: how healthy is the sales pipeline?


-- Query A: deals and value by stage
SELECT
  stage,
  COUNT(*) AS deals,
  ROUND(SUM(amount_usd), 2) AS total_amount_usd
FROM recruiting.sales_deals
GROUP BY stage
ORDER BY deals DESC;


-- Query B: win rate (closed deals only: won out of won + lost)
SELECT
  COUNTIF(stage = 'won') AS won,
  COUNTIF(stage = 'lost') AS lost,
  ROUND(100 * COUNTIF(stage = 'won') / COUNTIF(stage IN ('won', 'lost')), 1) AS win_rate_pct
FROM recruiting.sales_deals;
