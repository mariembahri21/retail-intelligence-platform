{{ config(
    materialized='incremental',
    unique_key='purchase_order_id',
    incremental_strategy='delete+insert'
) }}

-- Purchase-order fact: one row per order placed, loaded up to the clock date.
-- It records the expectation (what we asked for and when we expected it).
-- What really happened is in fct_deliveries.
--
-- There is no "was cancelled" column on purpose. Whether an order will be cancelled
-- is only known later (when the product leaves the shelf), so showing it on the day
-- of the order would leak the future.

select
    purchase_order_id,
    store_id,
    item_id,
    order_date,
    expected_date,
    ordered_units
from {{ ref('stg_sim_orders') }}
where order_date <= cast('{{ var("as_of_date") }}' as date)
{% if is_incremental() %}
  and order_date >= (select max(order_date) from {{ this }})
{% endif %}