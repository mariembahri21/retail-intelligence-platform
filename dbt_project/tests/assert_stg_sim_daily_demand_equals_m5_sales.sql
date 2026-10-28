-- Fails if the simulator's demand differs from the real M5 sales.
select d.store_id, d.item_id, d.date, d.demand_units as simulator_demand, s.demand_units as m5_demand
from {{ ref('stg_sim_daily') }} as d
join {{ ref('stg_m5_calendar') }} as c on c.date = d.date
join {{ ref('stg_m5_sales') }} as s
    on s.store_id = d.store_id and s.item_id = d.item_id and s.d = c.d
where d.demand_units != s.demand_units