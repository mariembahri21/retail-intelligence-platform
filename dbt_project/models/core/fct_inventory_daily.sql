{{ config(
    materialized='incremental',
    unique_key=['store_id', 'item_id', 'date'],
    incremental_strategy='delete+insert',
    on_schema_change='fail'
) }}

-- Inventory fact: one row per store, product and day (the simulator's daily record).
-- Same grain as fct_sales, so the two join one to one.
--
-- is_stockout: demand could not be fully served, i.e. lost_sales_units > 0.
-- stock_gap_units: what the computer believes minus what is really on the shelf.
--   Positive = ghost units in the computer (phantom stock).
-- Only days up to the clock date (var as_of_date) are loaded.

select
    cast(store_id as varchar) as store_id,
    cast(item_id as varchar) as item_id,
    cast(date as date) as date,
    cast(is_on_sale as boolean) as is_on_sale,
    cast(opening_units as integer) as opening_units,
    cast(received_units as integer) as received_units,
    cast(demand_units as integer) as demand_units,
    cast(sold_units as integer) as sold_units,
    cast(lost_sales_units as integer) as lost_sales_units,
    cast(expired_units as integer) as expired_units,
    cast(shrunk_units as integer) as shrunk_units,
    cast(cleared_units as integer) as cleared_units,
    cast(record_error_units as integer) as record_error_units,
    cast(count_adjustment_units as integer) as count_adjustment_units,
    cast(end_stock_units as integer) as end_stock_units,
    cast(system_stock_units as integer) as system_stock_units,
    cast(ordered_units as integer) as ordered_units,
    cast(on_order_units as integer) as on_order_units,
    cast(lost_sales_units > 0 as boolean) as is_stockout,
    cast(system_stock_units - end_stock_units as integer) as stock_gap_units
from {{ ref('stg_sim_daily') }}
where date <= cast('{{ var("as_of_date") }}' as date)
{% if is_incremental() %}
  and date >= (select max(date) from {{ this }})
{% endif %}