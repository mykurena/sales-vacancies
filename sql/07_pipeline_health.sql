-- 07_pipeline_health.sql
-- Pipeline health from the run log (recruiting.pipeline_runs, filled by monitoring/run_validations.py).


-- Query A: the most recent runs
SELECT
  started_at,
  run_type,
  status,
  checks_total,
  checks_failed,
  error_message
FROM recruiting.pipeline_runs
ORDER BY started_at DESC
LIMIT 20;


-- Query B: runs and problem rate by day
SELECT
  DATE(started_at) AS run_date,
  COUNT(*) AS runs,
  COUNTIF(status != 'success') AS runs_with_problems,
  ROUND(100 * COUNTIF(status != 'success') / COUNT(*), 1) AS problem_rate_pct
FROM recruiting.pipeline_runs
GROUP BY run_date
ORDER BY run_date DESC;


-- Query C: checks that are failing right now (from the latest audit_checks)
SELECT
  check_type,
  check_name,
  expected,
  actual,
  status
FROM recruiting.audit_checks
WHERE status = 'FAIL'
ORDER BY check_type, check_name;
