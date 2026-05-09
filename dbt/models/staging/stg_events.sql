-- Staging: clean & standardize raw events.
-- One row per event. No business logic here — just typing, filtering nulls,
-- and normalizing values so downstream models can trust the data.

with source as (
    select * from {{ source('raw', 'events_raw') }}
),

cleaned as (
    select
        cast(event_time as timestamp)               as event_at,
        lower(trim(event_type))                     as event_type,
        product_id,
        category_id,
        nullif(trim(category_code), '')             as category_code,
        nullif(trim(brand), '')                     as brand,
        cast(price as numeric(10, 2))               as price,
        user_id,
        nullif(trim(user_session), '')              as session_id,
        nullif(trim(user_session), '')              as user_session
    from source
    where event_time is not null
      and user_id    is not null
      and event_type in ('view', 'cart', 'purchase')
)

select * from cleaned
