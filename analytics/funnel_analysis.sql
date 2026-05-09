-- =====================================================================
-- FUNNEL ANALYSIS
-- Run against the `marts` schema (dbt) or the BigQuery `product_analytics` dataset.
-- =====================================================================

-- 1. Overall funnel with drop-off
SELECT
    stage,
    users,
    ROUND(pct_of_top * 100, 2)  AS pct_of_top,
    ROUND(pct_of_prev * 100, 2) AS pct_of_prev,
    ROUND((1 - pct_of_prev) * 100, 2) AS drop_off_pct
FROM marts.funnel
ORDER BY stage_order;


-- 2. Conversion rate (view → purchase) by week
SELECT
    DATE_TRUNC('week', event_at) AS week,
    COUNT(DISTINCT CASE WHEN event_type = 'view'     THEN user_id END) AS viewers,
    COUNT(DISTINCT CASE WHEN event_type = 'purchase' THEN user_id END) AS buyers,
    ROUND(
        COUNT(DISTINCT CASE WHEN event_type = 'purchase' THEN user_id END)::numeric
        / NULLIF(COUNT(DISTINCT CASE WHEN event_type = 'view' THEN user_id END), 0)
    , 4) AS conversion_rate
FROM staging.stg_events
GROUP BY 1
ORDER BY 1;


-- 3. Top categories by purchase volume
SELECT
    COALESCE(category_code, 'unknown') AS category,
    COUNT(*) AS purchases,
    SUM(price) AS revenue
FROM staging.stg_events
WHERE event_type = 'purchase'
GROUP BY 1
ORDER BY revenue DESC
LIMIT 20;
