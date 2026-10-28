-- Fails if sold + lost sales is not the demand on a day when the product is on sale.
select *
from {{ ref('stg_sim_daily') }}
where is_on_sale
  and sold_units + lost_sales_units != demand_units