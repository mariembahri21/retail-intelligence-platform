-- Fails if an order breaks the rules: late 0-4 days, arrival = expected + late days,
-- expected on or after the order day, delivered no more than ordered.
select *
from {{ ref('stg_sim_orders') }}
where days_late not between 0 and 4
   or arrival_date != expected_date + days_late
   or expected_date < order_date
   or delivered_units > ordered_units