-- 01_time_to_fill.sql
-- Question: how long does it take to fill a vacancy, and how many vacancies get filled?
-- Dataset: recruiting (BigQuery). Run each query on its own (select it, then Run).


-- Query A: average days to fill by department (filled vacancies only)
SELECT
  department,
  COUNT(*) AS filled_vacancies,
  ROUND(AVG(DATE_DIFF(closed_at, opened_at, DAY)), 1) AS avg_days_to_fill
FROM recruiting.vacancies
WHERE status = 'filled'
GROUP BY department
ORDER BY avg_days_to_fill DESC;


-- Query B: share of vacancies that ended up filled, by the month they were opened
-- Note: the most recent months look low because those vacancies have not had time to be filled yet.
SELECT
  DATE_TRUNC(opened_at, MONTH) AS opened_month,
  COUNT(*) AS vacancies_opened,
  COUNTIF(status = 'filled') AS vacancies_filled,
  ROUND(100 * COUNTIF(status = 'filled') / COUNT(*), 1) AS fill_rate_pct
FROM recruiting.vacancies
GROUP BY opened_month
ORDER BY opened_month;
