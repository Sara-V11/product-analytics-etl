-- =====================================================================
-- RETENTION ANALYSIS
-- =====================================================================

-- 1. Retention curve (averaged across all cohorts)
SELECT
    week_number,
    ROUND(AVG(retention_rate) * 100, 2) AS avg_retention_pct,
    SUM(retained_users) AS total_retained
FROM marts.retention
GROUP BY week_number
ORDER BY week_number;


-- 2. Cohort retention matrix (pivot-friendly)
SELECT
    cohort_week,
    cohort_users,
    MAX(CASE WHEN week_number = 0 THEN retention_rate END) AS w0,
    MAX(CASE WHEN week_number = 1 THEN retention_rate END) AS w1,
    MAX(CASE WHEN week_number = 2 THEN retention_rate END) AS w2,
    MAX(CASE WHEN week_number = 3 THEN retention_rate END) AS w3,
    MAX(CASE WHEN week_number = 4 THEN retention_rate END) AS w4
FROM marts.retention
GROUP BY cohort_week, cohort_users
ORDER BY cohort_week;


-- 3. Best & worst performing cohorts at week 1
SELECT
    cohort_week,
    cohort_users,
    retention_rate AS week_1_retention
FROM marts.retention
WHERE week_number = 1
ORDER BY retention_rate DESC
LIMIT 10;
