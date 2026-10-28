{{ config(severity='warn') }}
-- Warns if there are sales on days when the product has no price.
-- This is a property of the real M5 data, so it warns instead of failing.
select store_id, item_id, date, demand_units
from {{ ref('fct_sales') }}
where not is_on_sale
  and demand_units > 0