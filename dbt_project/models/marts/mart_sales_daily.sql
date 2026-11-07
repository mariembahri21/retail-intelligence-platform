-- Sales per day, for dashboards: one row per store, category and day.
--
-- demand_*  : what customers wanted to buy.
-- sold_*    : what the shelf could really sell.
-- revenue   : sold units x price (what the shop earned).
-- lost_revenue : lost sales x price (what the shop missed because of stockouts).
-- avg_price : demand_amount divided by the demand of products that were on sale.
-- revenue + lost_revenue = demand_amount.

select
    s.store_id,
    p.cat_id,
    s.date,
    sum(s.demand_units) as demand_units,
    sum(i.sold_units) as sold_units,
    sum(i.lost_sales_units) as lost_sales_units,
    sum(s.demand_amount) as demand_amount,
    sum(i.sold_units * s.sell_price) as revenue,
    sum(i.lost_sales_units * s.sell_price) as lost_revenue,
    sum(s.demand_amount)
        / nullif(sum(case when s.is_on_sale then s.demand_units end), 0) as avg_price
from {{ ref('fct_sales') }} as s
join {{ ref('fct_inventory_daily') }} as i
    on i.store_id = s.store_id and i.item_id = s.item_id and i.date = s.date
join {{ ref('dim_product') }} as p on p.item_id = s.item_id
group by s.store_id, p.cat_id, s.date