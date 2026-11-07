-- Fails if the units ordered on a day differ from the units ordered in the daily stock.
with ordered as (
    select store_id, item_id, order_date as date, sum(ordered_units) as ordered_units
    from {{ ref('fct_purchase_orders') }}
    group by store_id, item_id, order_date
)
select
    coalesce(i.store_id, o.store_id) as store_id,
    coalesce(i.item_id, o.item_id) as item_id,
    coalesce(i.date, o.date) as date,
    i.ordered_units as daily_ordered,
    o.ordered_units as orders_ordered
from {{ ref('fct_inventory_daily') }} as i
full outer join ordered as o
    on o.store_id = i.store_id and o.item_id = i.item_id and o.date = i.date
where coalesce(i.ordered_units, 0) != coalesce(o.ordered_units, 0)