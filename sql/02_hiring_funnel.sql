-- 02_hiring_funnel.sql
-- Question: where do candidates drop out of the hiring funnel, and which sourcing channels hire best?
-- furthest_stage is the last stage a candidate reached, so each stage count includes the later stages.


-- Query A: overall funnel
SELECT
  COUNT(*) AS applied,
  COUNTIF(furthest_stage IN ('screened', 'interview', 'offer', 'hired')) AS screened,
  COUNTIF(furthest_stage IN ('interview', 'offer', 'hired')) AS interviewed,
  COUNTIF(furthest_stage IN ('offer', 'hired')) AS offered,
  COUNTIF(furthest_stage = 'hired') AS hired
FROM recruiting.applications;


-- Query B: applications and hire rate by sourcing channel
SELECT
  c.source_channel,
  COUNT(*) AS applications,
  COUNTIF(a.furthest_stage = 'hired') AS hires,
  ROUND(100 * COUNTIF(a.furthest_stage = 'hired') / COUNT(*), 2) AS hire_rate_pct
FROM recruiting.applications AS a
JOIN recruiting.candidates AS c
  ON a.candidate_id = c.candidate_id
GROUP BY c.source_channel
ORDER BY hire_rate_pct DESC;
