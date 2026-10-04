-- 04_monthly_revenue.sql
-- Question: how much revenue do placements generate each month?
-- Revenue is the placement fee charged when a candidate is hired.

SELECT
  DATE_TRUNC(placed_at, MONTH) AS placement_month,
  COUNT(*) AS placements,
  ROUND(SUM(placement_fee_usd), 2) AS revenue_usd,
  ROUND(AVG(placement_fee_usd), 2) AS avg_fee_usd
FROM recruiting.placements
GROUP BY placement_month
ORDER BY placement_month;
