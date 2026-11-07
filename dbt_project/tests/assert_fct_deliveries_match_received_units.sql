-- Fails if the units delivered on a day differ from the units received in the daily stock.
with delivered as (
    select store_id, item_id, arrival_date as date, sum(delivered_units) as delivered_units
    from {{ ref('fct_deliveries') }}
    group by store_id, item_id, arrival_date
)
select
    coalesce(i.store_id, d.store_id) as store_id,
    coalesce(i.item_id, d.item_id) as item_id,
    coalesce(i.date, d.date) as date,
    i.received_units,
    d.delivered_units
from {{ ref('fct_inventory_daily') }} as i
full outer join delivered as d
    on d.store_id = i.store_id and d.item_id = i.item_id and d.date = i.date
where coalesce(i.received_units, 0) != coalesce(d.delivered_units, 0)