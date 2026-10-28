-- Orders placed by the simulated shop: one row per order.
-- The simulator stores days as numbers (0 = first day). We turn them into dates
-- with the calendar, and we create purchase_order_id, because the data has none.

with calendar as (
    select date, cast(substr(d, 3) as integer) - 1 as day_number
    from {{ ref('stg_m5_calendar') }}
)

select
    md5(o.store_id || '|' || o.item_id || '|' || cast(order_day.date as varchar)) as purchase_order_id,
    o.store_id,
    o.item_id,
    order_day.date as order_date,
    expected_day.date as expected_date,
    arrival_day.date as arrival_date,
    o.ordered_qty as ordered_units,
    o.delivered_qty as delivered_units,
    o.late_days as days_late,
    o.cancelled as was_cancelled
from {{ source('sim_files', 'orders') }} as o
left join calendar as order_day on order_day.day_number = o.order_day
left join calendar as expected_day on expected_day.day_number = o.expected_day
left join calendar as arrival_day on arrival_day.day_number = o.arrival_day