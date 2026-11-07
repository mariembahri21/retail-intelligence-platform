{{ config(
    materialized='incremental',
    unique_key=['store_id', 'item_id', 'date'],
    incremental_strategy='delete+insert'
) }}

-- Inventory fact: one row per store, product and day (the simulator's daily record).
-- Same grain as fct_sales, so the two join one to one.
--
-- is_stockout: demand could not be fully served, i.e. lost_sales_units > 0.
-- stock_gap_units: what the computer believes minus what is really on the shelf.
--   Positive = ghost units in the computer (phantom stock).
-- Only days up to the clock date (var as_of_date) are loaded.

select
    store_id,
    item_id,
    date,
    is_on_sale,
    opening_units,
    received_units,
    demand_units,
    sold_units,
    lost_sales_units,
    expired_units,
    shrunk_units,
    cleared_units,
    record_error_units,
    count_adjustment_units,
    end_stock_units,
    system_stock_units,
    ordered_units,
    on_order_units,
    lost_sales_units > 0 as is_stockout,
    system_stock_units - end_stock_units as stock_gap_units
from {{ ref('stg_sim_daily') }}
where date <= cast('{{ var("as_of_date") }}' as date)
{% if is_incremental() %}
  and date >= (select max(date) from {{ this }})
{% endif %}