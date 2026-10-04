-- 06_validation_checks.sql
-- Data validation and reconciliation checks. Results are stored in recruiting.audit_checks.
--
-- Each row of the audit table is one check:
--   expected / actual  what the check compared
--   difference         actual - expected
--   status             PASS when actual equals expected, FAIL otherwise
--
-- Check types:
--   integrity       keys exist and are unique
--   reconciliation  totals agree between tables, or between raw data and an aggregation
--   validity        values and dates make business sense
--
-- Run this whole file as one statement, then read the results with:
--   SELECT * FROM recruiting.audit_checks ORDER BY status DESC, check_type, check_name;

CREATE OR REPLACE TABLE recruiting.audit_checks AS
WITH monthly_revenue AS (
  SELECT
    DATE_TRUNC(placed_at, MONTH) AS placement_month,
    SUM(placement_fee_usd) AS revenue_usd
  FROM recruiting.placements
  GROUP BY placement_month
),

checks AS (

  -- INTEGRITY ---------------------------------------------------------------

  SELECT
    'integrity' AS check_type,
    'orphan_vacancies_client' AS check_name,
    'Every vacancy belongs to an existing client' AS description,
    CAST(0 AS FLOAT64) AS expected,
    CAST(COUNT(*) AS FLOAT64) AS actual
  FROM recruiting.vacancies AS v
  LEFT JOIN recruiting.clients AS c ON v.client_id = c.client_id
  WHERE c.client_id IS NULL

  UNION ALL
  SELECT
    'integrity', 'orphan_applications_vacancy',
    'Every application points to an existing vacancy',
    CAST(0 AS FLOAT64), CAST(COUNT(*) AS FLOAT64)
  FROM recruiting.applications AS a
  LEFT JOIN recruiting.vacancies AS v ON a.vacancy_id = v.vacancy_id
  WHERE v.vacancy_id IS NULL

  UNION ALL
  SELECT
    'integrity', 'orphan_applications_candidate',
    'Every application points to an existing candidate',
    CAST(0 AS FLOAT64), CAST(COUNT(*) AS FLOAT64)
  FROM recruiting.applications AS a
  LEFT JOIN recruiting.candidates AS c ON a.candidate_id = c.candidate_id
  WHERE c.candidate_id IS NULL

  UNION ALL
  SELECT
    'integrity', 'orphan_placements_vacancy',
    'Every placement points to an existing vacancy',
    CAST(0 AS FLOAT64), CAST(COUNT(*) AS FLOAT64)
  FROM recruiting.placements AS p
  LEFT JOIN recruiting.vacancies AS v ON p.vacancy_id = v.vacancy_id
  WHERE v.vacancy_id IS NULL

  UNION ALL
  SELECT
    'integrity', 'duplicate_vacancy_id',
    'vacancy_id is unique',
    CAST(0 AS FLOAT64), CAST(COUNT(*) - COUNT(DISTINCT vacancy_id) AS FLOAT64)
  FROM recruiting.vacancies

  UNION ALL
  SELECT
    'integrity', 'duplicate_application_id',
    'application_id is unique',
    CAST(0 AS FLOAT64), CAST(COUNT(*) - COUNT(DISTINCT application_id) AS FLOAT64)
  FROM recruiting.applications

  UNION ALL
  SELECT
    'integrity', 'duplicate_placement_id',
    'placement_id is unique',
    CAST(0 AS FLOAT64), CAST(COUNT(*) - COUNT(DISTINCT placement_id) AS FLOAT64)
  FROM recruiting.placements

  -- RECONCILIATION ----------------------------------------------------------

  UNION ALL
  SELECT
    'reconciliation', 'placements_vs_filled_vacancies',
    'Number of placements equals number of filled vacancies',
    CAST((SELECT COUNT(*) FROM recruiting.vacancies WHERE status = 'filled') AS FLOAT64),
    CAST((SELECT COUNT(*) FROM recruiting.placements) AS FLOAT64)

  UNION ALL
  SELECT
    'reconciliation', 'hired_applications_vs_placements',
    'Number of applications that reached "hired" equals number of placements',
    CAST((SELECT COUNTIF(furthest_stage = 'hired') FROM recruiting.applications) AS FLOAT64),
    CAST((SELECT COUNT(*) FROM recruiting.placements) AS FLOAT64)

  UNION ALL
  SELECT
    'reconciliation', 'placements_without_hired_application',
    'Every placement has a matching "hired" application (same vacancy and candidate)',
    CAST(0 AS FLOAT64), CAST(COUNT(*) AS FLOAT64)
  FROM recruiting.placements AS p
  LEFT JOIN recruiting.applications AS a
    ON p.vacancy_id = a.vacancy_id
   AND p.candidate_id = a.candidate_id
   AND a.furthest_stage = 'hired'
  WHERE a.application_id IS NULL

  UNION ALL
  SELECT
    'reconciliation', 'revenue_total_vs_monthly_report',
    'Total fees in placements equals the monthly revenue report (no fee lost because of a missing date)',
    CAST((SELECT SUM(placement_fee_usd) FROM recruiting.placements) AS FLOAT64),
    CAST((SELECT SUM(revenue_usd) FROM monthly_revenue WHERE placement_month IS NOT NULL) AS FLOAT64)

  UNION ALL
  SELECT
    'reconciliation', 'revenue_total_vs_filled_vacancies',
    'Total fees in placements equals the fees that belong to filled vacancies',
    CAST((SELECT SUM(placement_fee_usd) FROM recruiting.placements) AS FLOAT64),
    CAST((
      SELECT SUM(p.placement_fee_usd)
      FROM recruiting.placements AS p
      JOIN recruiting.vacancies AS v ON p.vacancy_id = v.vacancy_id
      WHERE v.status = 'filled'
    ) AS FLOAT64)

  -- VALIDITY ----------------------------------------------------------------

  UNION ALL
  SELECT
    'validity', 'filled_vacancies_missing_close_date',
    'Filled vacancies have a close date',
    CAST(0 AS FLOAT64), CAST(COUNT(*) AS FLOAT64)
  FROM recruiting.vacancies
  WHERE status = 'filled' AND closed_at IS NULL

  UNION ALL
  SELECT
    'validity', 'open_vacancies_with_close_date',
    'Open vacancies have no close date',
    CAST(0 AS FLOAT64), CAST(COUNT(*) AS FLOAT64)
  FROM recruiting.vacancies
  WHERE status = 'open' AND closed_at IS NOT NULL

  UNION ALL
  SELECT
    'validity', 'closed_before_opened',
    'No vacancy closes before it opens',
    CAST(0 AS FLOAT64), CAST(COUNT(*) AS FLOAT64)
  FROM recruiting.vacancies
  WHERE closed_at < opened_at

  UNION ALL
  SELECT
    'validity', 'negative_or_missing_marketing_spend',
    'Marketing spend is present and not negative',
    CAST(0 AS FLOAT64), CAST(COUNT(*) AS FLOAT64)
  FROM recruiting.marketing_daily
  WHERE spend_usd IS NULL OR spend_usd < 0

  UNION ALL
  SELECT
    'validity', 'clicks_exceed_impressions',
    'Clicks never exceed impressions',
    CAST(0 AS FLOAT64), CAST(COUNT(*) AS FLOAT64)
  FROM recruiting.marketing_daily
  WHERE clicks > impressions

  UNION ALL
  SELECT
    'validity', 'won_deals_without_client',
    'Won deals are linked to a client',
    CAST(0 AS FLOAT64), CAST(COUNT(*) AS FLOAT64)
  FROM recruiting.sales_deals
  WHERE stage = 'won' AND client_id IS NULL

  UNION ALL
  SELECT
    'validity', 'closed_deals_without_close_date',
    'Won and lost deals have a close date',
    CAST(0 AS FLOAT64), CAST(COUNT(*) AS FLOAT64)
  FROM recruiting.sales_deals
  WHERE stage IN ('won', 'lost') AND closed_at IS NULL
)

SELECT
  check_type,
  check_name,
  description,
  expected,
  actual,
  actual - expected AS difference,
  IF(ABS(actual - expected) < 0.005, 'PASS', 'FAIL') AS status,
  CURRENT_TIMESTAMP() AS checked_at
FROM checks;
