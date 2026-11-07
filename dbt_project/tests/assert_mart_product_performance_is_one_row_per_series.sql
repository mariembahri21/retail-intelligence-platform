-- Fails if the product mart has duplicates or loses products compared with the classes.
select *
from (
    select
        (select count(*) from {{ ref('mart_product_performance') }}) as mart_rows,
        (select count(distinct store_id || '|' || item_id) from {{ ref('mart_product_performance') }}) as mart_series,
        (select count(*) from {{ ref('dim_product_class') }}) as class_rows
)
where mart_rows != mart_series or mart_rows != class_rows