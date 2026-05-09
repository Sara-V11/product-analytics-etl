-- =====================================================================
-- TOP-LINE KPIs
-- These power the portfolio dashboard.
-- =====================================================================

-- 1. Headline metrics
SELECT
    COUNT(DISTINCT user_id)                                   AS total_users,
    COUNT(DISTINCT session_id)                                AS total_sessions,
    COUNT(*)                                                  AS total_events,
    COUNT(DISTINCT CASE WHEN event_type='purchase' THEN user_id END) AS paying_users,
    COALESCE(SUM(CASE WHEN event_type='purchase' THEN price ELSE 0 END), 0) AS gmv
FROM staging.stg_events;


-- 2. DAU / WAU / MAU
SELECT
    DATE_TRUNC('day', event_at)::date AS day,
    COUNT(DISTINCT user_id)           AS dau
FROM staging.stg_events
GROUP BY 1
ORDER BY 1;


-- 3. Average revenue per paying user (ARPPU)
SELECT
    user_id,
    SUM(price) AS revenue
FROM staging.stg_events
WHERE event_type = 'purchase'
GROUP BY user_id
ORDER BY revenue DESC;


-- 4. Average session duration & events per session
SELECT
    ROUND(AVG(duration_minutes), 2) AS avg_session_minutes,
    ROUND(AVG(total_events), 2)     AS avg_events_per_session,
    ROUND(AVG(CASE WHEN converted THEN 1.0 ELSE 0.0 END) * 100, 2) AS session_conversion_pct
FROM intermediate.sessions;
