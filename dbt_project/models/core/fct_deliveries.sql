{{ config(
    materialized='incremental',
    unique_key='delivery_id',
    incremental_strategy='delete+insert',
    on_schema_change='fail'
) }}

-- Delivery fact: one row per delivery received (one per delivered order),
-- loaded up to the clock date by arrival date.
--
-- Not included:
--   - cancelled orders (the product left the shelf, nothing arrived);
--   - orders that arrive after the clock date (they have not arrived yet).
--
-- On time : the delivery arrives on the promised day (days_late = 0).
-- In full : the quantity received is at least the quantity ordered.
-- OTIF    : on time AND in full. No tolerance is applied.

select
    cast(md5('delivery|' || purchase_order_id) as varchar) as delivery_id,
    cast(purchase_order_id as varchar) as purchase_order_id,
    cast(store_id as varchar) as store_id,
    cast(item_id as varchar) as item_id,
    cast(arrival_date as date) as arrival_date,
    cast(ordered_units as integer) as ordered_units,
    cast(delivered_units as integer) as delivered_units,
    cast(days_late as integer) as days_late,
    cast(date_diff('day', order_date, expected_date) as bigint) as promised_lead_days,
    cast(date_diff('day', order_date, arrival_date) as bigint) as actual_lead_days,
    cast(delivered_units * 1.0 / ordered_units as double) as fill_rate,
    days_late = 0 as is_on_time,
    delivered_units >= ordered_units as is_in_full,
    (days_late = 0 and delivered_units >= ordered_units) as is_otif
from {{ ref('stg_sim_orders') }}
where not was_cancelled
  and arrival_date <= cast('{{ var("as_of_date") }}' as date)
{% if is_incremental() %}
  and arrival_date >= (select max(arrival_date) from {{ this }})
{% endif %}