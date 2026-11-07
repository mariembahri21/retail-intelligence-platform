-- Product performance, one row per store and product, over the last 52 weeks.
-- Numbers behind the ABC and XYZ classes, plus a 28-day trend.
--
-- trend_28d = (units in the last 28 days - units in the 28 days before) / units before.
-- It is null when the product sold nothing in the 28 days before.

with today as (
    select max(date) as last_day from {{ ref('fct_sales') }}
),

recent as (
    select
        s.store_id,
        s.item_id,
        sum(s.demand_units) as units_52w,
        coalesce(sum(s.demand_units) filter (where s.date > t.last_day - 28), 0) as units_last_28d,
        coalesce(sum(s.demand_units) filter (
            where s.date > t.last_day - 56 and s.date <= t.last_day - 28), 0) as units_prev_28d
    from {{ ref('fct_sales') }} as s
    cross join today as t
    where s.date > t.last_day - 364
    group by s.store_id, s.item_id
)

select
    c.store_id,
    c.item_id,
    p.cat_id,
    c.abc_class,
    c.xyz_class,
    r.units_52w,
    c.revenue_amount_52w,
    c.revenue_rank,
    c.cumulative_revenue_share,
    r.units_last_28d,
    r.units_prev_28d,
    (r.units_last_28d - r.units_prev_28d) * 1.0 / nullif(r.units_prev_28d, 0) as trend_28d
from {{ ref('dim_product_class') }} as c
join recent as r on r.store_id = c.store_id and r.item_id = c.item_id
join {{ ref('dim_product') }} as p on p.item_id = c.item_id