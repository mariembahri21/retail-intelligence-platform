-- Fails if the simulator output has more or fewer rows than the M5 sales.
select *
from (
    select
        (select count(*) from {{ ref('stg_sim_daily') }}) as simulator_rows,
        (select count(*) from {{ ref('stg_m5_sales') }}) as m5_rows
)
where simulator_rows != m5_rows