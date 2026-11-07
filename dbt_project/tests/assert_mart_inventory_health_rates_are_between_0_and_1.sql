-- Fails if a rate leaves the 0 to 1 range, or a turnover / cover is negative.
select *
from {{ ref('mart_inventory_health') }}
where overstock_day_rate not between 0 and 1
   or stockout_day_rate not between 0 and 1
   or waste_rate not between 0 and 1
   or turnover < 0
   or days_of_cover < 0