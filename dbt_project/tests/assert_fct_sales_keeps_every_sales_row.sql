-- Fails if the joins lost or duplicated rows compared with the staging sales.
select *
from (
    select
        (select count(*) from {{ ref('fct_sales') }}) as fact_rows,
        (select count(*) from {{ ref('stg_m5_sales') }}) as staging_rows
)
where fact_rows != staging_rows