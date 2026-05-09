-- Mart: weekly retention matrix.
-- For each cohort (week of first event), measures % of users who returned
-- in week 0, 1, 2, ... N relative to their cohort start.

with cohort as (
    select * from {{ ref('cohort') }}
),

events as (
    select * from {{ ref('stg_events') }}
),

user_weeks as (
    select distinct
        e.user_id,
        date_trunc('week', e.event_at)::date as activity_week
    from events e
),

joined as (
    select
        c.cohort_week,
        c.user_id,
        u.activity_week,
        ((u.activity_week - c.cohort_week) / 7)::int as week_number
    from cohort c
    join user_weeks u using (user_id)
    where u.activity_week >= c.cohort_week
),

cohort_size as (
    select cohort_week, count(distinct user_id) as cohort_users
    from cohort
    group by cohort_week
),

retention as (
    select
        cohort_week,
        week_number,
        count(distinct user_id) as retained_users
    from joined
    group by cohort_week, week_number
)

select
    r.cohort_week,
    r.week_number,
    r.retained_users,
    cs.cohort_users,
    round(r.retained_users::numeric / nullif(cs.cohort_users, 0), 4) as retention_rate
from retention r
join cohort_size cs using (cohort_week)
order by r.cohort_week, r.week_number
