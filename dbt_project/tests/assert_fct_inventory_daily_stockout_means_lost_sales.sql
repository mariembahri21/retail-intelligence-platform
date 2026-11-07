-- Fails if sold + lost does not give the demand, or if is_stockout disagrees with lost sales.
select *
from {{ ref('fct_inventory_daily') }}
where (is_on_sale and sold_units + lost_sales_units != demand_units)
   or (is_stockout != (lost_sales_units > 0))