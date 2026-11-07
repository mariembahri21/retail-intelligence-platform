-- Fails if the two daily facts do not have the same rows.
select *
from (
    select
        (select count(*) from {{ ref('fct_inventory_daily') }}) as inventory_rows,
        (select count(*) from {{ ref('fct_sales') }}) as sales_rows
)
where inventory_rows != sales_rows