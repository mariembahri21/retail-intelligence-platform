-- Fails if the joins lost or duplicated rows compared with the staging sales
-- (up to the clock date).
select *
from (
    select
        (select count(*) from {{ ref('fct_sales') }}) as fact_rows,
        (select count(*)
         from {{ ref('stg_m5_sales') }} as s
         join {{ ref('stg_m5_calendar') }} as c on c.d = s.d
         where c.date <= cast('{{ var("as_of_date") }}' as date)) as staging_rows
)
where fact_rows != staging_rows