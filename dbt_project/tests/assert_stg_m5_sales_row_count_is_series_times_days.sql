-- Fails if rows are lost or duplicated: rows must equal series x days.
with counts as (
    select
        count(*) as n_rows,
        count(distinct store_id || '|' || item_id) as n_series,
        count(distinct d) as n_days
    from {{ ref('stg_m5_sales') }}
)
select *
from counts
where n_rows != n_series * n_days