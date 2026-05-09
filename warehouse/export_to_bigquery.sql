-- BigQuery DDL for analytics-ready tables.
-- These mirror the dbt marts and are populated when running dbt with target=prod.
-- Partitioning + clustering keep query costs low.

CREATE SCHEMA IF NOT EXISTS `${GCP_PROJECT_ID}.product_analytics`
OPTIONS (location = 'US');

-- Funnel: small lookup-style table, no partitioning needed.
CREATE TABLE IF NOT EXISTS `${GCP_PROJECT_ID}.product_analytics.funnel` (
    stage         STRING  NOT NULL,
    stage_order   INT64   NOT NULL,
    users         INT64   NOT NULL,
    pct_of_top    FLOAT64,
    pct_of_prev   FLOAT64
);

-- Cohort: partition by cohort_month for efficient lookups.
CREATE TABLE IF NOT EXISTS `${GCP_PROJECT_ID}.product_analytics.cohort` (
    user_id        INT64    NOT NULL,
    first_event_at TIMESTAMP,
    cohort_week    DATE,
    cohort_month   DATE
)
PARTITION BY cohort_month
CLUSTER BY user_id;

-- Retention: partition by cohort_week, cluster by week_number.
CREATE TABLE IF NOT EXISTS `${GCP_PROJECT_ID}.product_analytics.retention` (
    cohort_week     DATE    NOT NULL,
    week_number     INT64   NOT NULL,
    retained_users  INT64,
    cohort_users    INT64,
    retention_rate  FLOAT64
)
PARTITION BY cohort_week
CLUSTER BY week_number;

-- Sessions: partition by session_start date for time-window queries.
CREATE TABLE IF NOT EXISTS `${GCP_PROJECT_ID}.product_analytics.sessions` (
    session_key      STRING NOT NULL,
    user_id          INT64,
    session_seq      INT64,
    session_start    TIMESTAMP,
    session_end      TIMESTAMP,
    duration_minutes FLOAT64,
    total_events     INT64,
    views            INT64,
    carts            INT64,
    purchases        INT64,
    revenue          NUMERIC,
    converted        BOOL
)
PARTITION BY DATE(session_start)
CLUSTER BY user_id;
