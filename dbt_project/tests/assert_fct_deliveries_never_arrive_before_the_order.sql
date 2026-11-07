-- Fails if a delivery arrives before its order was placed, or for another store or product.
select d.delivery_id, o.order_date, d.arrival_date
from {{ ref('fct_deliveries') }} as d
join {{ ref('fct_purchase_orders') }} as o on o.purchase_order_id = d.purchase_order_id
where d.arrival_date < o.order_date
   or d.store_id != o.store_id
   or d.item_id != o.item_id