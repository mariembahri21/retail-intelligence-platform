-- Delivery fact: one row per delivery received (one per delivered order).
--
-- Not included:
--   - cancelled orders (the product left the shelf, nothing arrived);
--   - orders that would arrive after the last simulated day.
--
-- On time : the delivery arrives on the promised day (days_late = 0).
-- In full : the quantity received is at least the quantity ordered.
-- OTIF    : on time AND in full. No tolerance is applied.

select
    md5('delivery|' || purchase_order_id) as delivery_id,
    purchase_order_id,
    store_id,
    item_id,
    arrival_date,
    ordered_units,
    delivered_units,
    days_late,
    date_diff('day', order_date, expected_date) as promised_lead_days,
    date_diff('day', order_date, arrival_date) as actual_lead_days,
    delivered_units * 1.0 / ordered_units as fill_rate,
    days_late = 0 as is_on_time,
    delivered_units >= ordered_units as is_in_full,
    (days_late = 0 and delivered_units >= ordered_units) as is_otif
from {{ ref('stg_sim_orders') }}
where not was_cancelled
  and arrival_date <= (select max(date) from {{ ref('stg_sim_daily') }})