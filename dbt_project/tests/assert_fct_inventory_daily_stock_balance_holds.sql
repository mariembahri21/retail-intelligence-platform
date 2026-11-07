-- Fails if the shelf stock does not add up: for every day after the first,
-- end stock = yesterday's end stock + launch delivery + received - sold - expired - shrunk - cleared.
with with_yesterday as (
    select
        store_id, item_id, date,
        end_stock_units, opening_units, received_units, sold_units,
        expired_units, shrunk_units, cleared_units,
        lag(end_stock_units) over (partition by store_id, item_id order by date) as yesterday_end_stock_units
    from {{ ref('fct_inventory_daily') }}
)
select *
from with_yesterday
where yesterday_end_stock_units is not null
  and end_stock_units != yesterday_end_stock_units + opening_units + received_units
                         - sold_units - expired_units - shrunk_units - cleared_units