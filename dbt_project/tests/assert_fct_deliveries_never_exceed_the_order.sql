-- Fails if a delivery brings more than the order asked for, or repeats a different quantity
-- than the order it answers.
select d.delivery_id, d.delivered_units, d.ordered_units, o.ordered_units as order_ordered_units
from {{ ref('fct_deliveries') }} as d
join {{ ref('fct_purchase_orders') }} as o on o.purchase_order_id = d.purchase_order_id
where d.delivered_units > o.ordered_units
   or d.ordered_units != o.ordered_units