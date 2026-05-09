-- Mart: funnel analysis.
-- For each user, find first time they hit each funnel stage.
-- Then aggregate to get stage-level counts and conversion rates.

with events as (
    select * from {{ ref('stg_events') }}
),

user_first_touch as (
    select
        user_id,
        min(case when event_type = 'view'     then event_at end) as first_view_at,
        min(case when event_type = 'cart'     then event_at end) as first_cart_at,
        min(case when event_type = 'purchase' then event_at end) as first_purchase_at
    from events
    group by user_id
),

stage_flags as (
    select
        user_id,
        first_view_at     is not null as reached_view,
        first_cart_at     is not null as reached_cart,
        first_purchase_at is not null as reached_purchase
    from user_first_touch
),

stage_counts as (
    select
        sum(case when reached_view     then 1 else 0 end) as users_view,
        sum(case when reached_cart     then 1 else 0 end) as users_cart,
        sum(case when reached_purchase then 1 else 0 end) as users_purchase
    from stage_flags
)

select
    'view'      as stage, 1 as stage_order, users_view     as users,
    1.0                                            as pct_of_top,
    1.0                                            as pct_of_prev
from stage_counts

union all

select
    'cart'      as stage, 2 as stage_order, users_cart     as users,
    users_cart::numeric    / nullif(users_view, 0) as pct_of_top,
    users_cart::numeric    / nullif(users_view, 0) as pct_of_prev
from stage_counts

union all

select
    'purchase'  as stage, 3 as stage_order, users_purchase as users,
    users_purchase::numeric / nullif(users_view, 0) as pct_of_top,
    users_purchase::numeric / nullif(users_cart, 0) as pct_of_prev
from stage_counts
