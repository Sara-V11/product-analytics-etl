-- Mart: cohort table.
-- Assigns every user to a weekly acquisition cohort based on their first event.

with events as (
    select * from {{ ref('stg_events') }}
),

first_seen as (
    select
        user_id,
        min(event_at) as first_event_at
    from events
    group by user_id
)

select
    user_id,
    first_event_at,
    date_trunc('week', first_event_at)::date as cohort_week,
    date_trunc('month', first_event_at)::date as cohort_month
from first_seen
