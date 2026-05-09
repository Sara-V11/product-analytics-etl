-- Intermediate: sessionization.
-- A new session starts when there's >30 min of inactivity for a user.
-- Output: one row per (user, session) with start time, end time, event counts.

with events as (
    select * from {{ ref('stg_events') }}
),

with_lag as (
    select
        user_id,
        session_id,
        event_at,
        event_type,
        product_id,
        price,
        lag(event_at) over (
            partition by user_id order by event_at
        ) as prev_event_at
    from events
),

session_flags as (
    select
        *,
        case
            when prev_event_at is null
              or extract(epoch from (event_at - prev_event_at)) > 1800
            then 1 else 0
        end as is_new_session
    from with_lag
),

session_ids as (
    select
        *,
        sum(is_new_session) over (
            partition by user_id order by event_at
            rows between unbounded preceding and current row
        ) as session_seq
    from session_flags
),

aggregated as (
    select
        user_id,
        session_seq,
        min(event_at)                                       as session_start,
        max(event_at)                                       as session_end,
        count(*)                                            as total_events,
        sum(case when event_type = 'view'     then 1 else 0 end) as views,
        sum(case when event_type = 'cart'     then 1 else 0 end) as carts,
        sum(case when event_type = 'purchase' then 1 else 0 end) as purchases,
        sum(case when event_type = 'purchase' then price else 0 end) as revenue
    from session_ids
    group by user_id, session_seq
)

select
    {{ dbt_utils.generate_surrogate_key(['user_id', 'session_seq']) }} as session_key,
    user_id,
    session_seq,
    session_start,
    session_end,
    extract(epoch from (session_end - session_start)) / 60.0 as duration_minutes,
    total_events,
    views,
    carts,
    purchases,
    revenue,
    case when purchases > 0 then true else false end as converted
from aggregated
