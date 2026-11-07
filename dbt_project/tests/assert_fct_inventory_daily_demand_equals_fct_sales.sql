-- Fails if the inventory record and the sales record disagree on demand.
select i.store_id, i.item_id, i.date, i.demand_units as inventory_demand, s.demand_units as sales_demand
from {{ ref('fct_inventory_daily') }} as i
join {{ ref('fct_sales') }} as s
    on s.store_id = i.store_id and s.item_id = i.item_id and s.date = i.date
where i.demand_units != s.demand_units