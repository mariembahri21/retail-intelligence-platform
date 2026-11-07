{{ config(
    materialized='incremental',
    unique_key=['store_id', 'item_id', 'date'],
    incremental_strategy='delete+insert'
) }}

-- Demand fact: one row per store, product and day (the real M5 sales).
-- Left joins keep every sales row. is_on_sale is true when a price exists
-- for that store, product and week; days before a product is listed are
-- not real zeros, and this flag lets us tell them apart.
--
-- Only days up to the clock date (var as_of_date) are loaded. An incremental run
-- reloads the last loaded day and everything after it; the unique key replaces
-- rows instead of duplicating them.

select
    s.store_id,
    s.item_id,
    c.date,
    s.demand_units,
    p.sell_price,
    (p.sell_price is not null) as is_on_sale,
    s.demand_units * p.sell_price as demand_amount
from {{ ref('stg_m5_sales') }} as s
join {{ ref('stg_m5_calendar') }} as c on c.d = s.d
left join {{ ref('stg_m5_prices') }} as p
    on p.store_id = s.store_id
   and p.item_id = s.item_id
   and p.wm_yr_wk = c.wm_yr_wk
where c.date <= cast('{{ var("as_of_date") }}' as date)
{% if is_incremental() %}
  and c.date >= (select max(date) from {{ this }})
{% endif %}