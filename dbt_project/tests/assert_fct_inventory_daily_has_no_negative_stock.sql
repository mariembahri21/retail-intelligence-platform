-- Fails if any stock or flow quantity is negative.
-- (record_error_units, count_adjustment_units and stock_gap_units can be negative by design.)
select *
from {{ ref('fct_inventory_daily') }}
where opening_units < 0 or received_units < 0 or demand_units < 0 or sold_units < 0
   or lost_sales_units < 0 or expired_units < 0 or shrunk_units < 0 or cleared_units < 0
   or end_stock_units < 0 or system_stock_units < 0 or ordered_units < 0 or on_order_units < 0