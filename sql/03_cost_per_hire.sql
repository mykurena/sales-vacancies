-- 03_cost_per_hire.sql
-- Question: how much does each paid channel spend per hire?
-- Referral and Outbound have no paid spend, so their cost per hire is NULL (not zero).

WITH spend AS (
  SELECT
    channel,
    SUM(spend_usd) AS total_spend_usd
  FROM recruiting.marketing_daily
  GROUP BY channel
),

hires AS (
  SELECT
    c.source_channel AS channel,
    COUNT(*) AS hires
  FROM recruiting.applications AS a
  JOIN recruiting.candidates AS c
    ON a.candidate_id = c.candidate_id
  WHERE a.furthest_stage = 'hired'
  GROUP BY c.source_channel
)

SELECT
  h.channel,
  h.hires,
  ROUND(s.total_spend_usd, 2) AS total_spend_usd,
  ROUND(SAFE_DIVIDE(s.total_spend_usd, h.hires), 2) AS cost_per_hire_usd
FROM hires AS h
LEFT JOIN spend AS s
  ON h.channel = s.channel
ORDER BY cost_per_hire_usd;
