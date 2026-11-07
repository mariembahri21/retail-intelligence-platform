-- Fails if a store-product-week appears twice, if a week has more than 7 days,
-- or if the weekly units do not add up to the daily facts (days on sale only).
select 'duplicate or too many days' as problem
from {{ ref('mart_inventory_health') }}
group by store_id, item_id, week_start_date
having count(*) > 1
union all
select 'too many days' from {{ ref('mart_inventory_health') }} where days_on_sale > 7 or days_on_sale < 1
union all
select 'units differ'
where (select sum(sold_units) from {{ ref('mart_inventory_health') }})
   != (select sum(sold_units) from {{ ref('fct_inventory_daily') }} where is_on_sale)
   or (select sum(lost_sales_units) from {{ ref('mart_inventory_health') }})
   != (select sum(lost_sales_units) from {{ ref('fct_inventory_daily') }} where is_on_sale)