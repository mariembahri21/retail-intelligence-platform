-- Fails if the daily mart does not add up to the facts, or if a store-category-day appears twice.
select 'units differ' as problem
where (select sum(demand_units) from {{ ref('mart_sales_daily') }})
   != (select sum(demand_units) from {{ ref('fct_sales') }})
   or (select sum(lost_sales_units) from {{ ref('mart_sales_daily') }})
   != (select sum(lost_sales_units) from {{ ref('fct_inventory_daily') }})
union all
select 'duplicate row'
from {{ ref('mart_sales_daily') }}
group by store_id, cat_id, date
having count(*) > 1