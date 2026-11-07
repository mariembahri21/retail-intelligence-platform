-- Fails if a (store, product) has two classes, or if a series with sales has none.
select *
from (
    select
        (select count(*) from {{ ref('dim_product_class') }}) as class_rows,
        (select count(distinct store_id || '|' || item_id) from {{ ref('dim_product_class') }}) as class_series,
        (select count(distinct store_id || '|' || item_id) from {{ ref('fct_sales') }}) as sales_series
)
where class_rows != class_series or class_series != sales_series