-- Product classes, one row per store and product, over the last 52 weeks
-- (364 days ending on the latest loaded day, i.e. the clock date).
--
-- ABC (importance, by revenue within each store):
--   A = the products that make the first 80% of the store's revenue,
--   B = the next 15%, C = the last 5% (including products with no revenue).
--   A product is A, B or C according to the share of revenue BEFORE it is added,
--   so the product that crosses the 80% line is still an A.
--
-- XYZ (predictability, by the coefficient of variation of weekly demand):
--   X below 0.5, Y from 0.5 to below 1.0, Z from 1.0 up.
--   Only weeks in which the product was on sale count, and a product needs at
--   least 4 such weeks; otherwise xyz_class is null (not enough history).
--
-- Revenue here is demand_amount (demand x price): the value of what customers wanted,
-- so a product is not penalised because it ran out of stock.

with today as (
    select max(date) as last_day from {{ ref('fct_sales') }}
),

window_sales as (
    select
        s.store_id,
        s.item_id,
        s.demand_units,
        s.demand_amount,
        s.is_on_sale,
        date_diff('day', s.date, t.last_day) // 7 as weeks_ago      -- 0 to 51, 7 days each
    from {{ ref('fct_sales') }} as s
    cross join today as t
    where s.date > t.last_day - 364
),

revenue as (
    select
        store_id,
        item_id,
        coalesce(sum(demand_amount), 0) as revenue_amount_52w
    from window_sales
    group by store_id, item_id
),

ranked as (
    select
        store_id,
        item_id,
        revenue_amount_52w,
        row_number() over (
            partition by store_id order by revenue_amount_52w desc, item_id
        ) as revenue_rank,
        sum(revenue_amount_52w) over (
            partition by store_id order by revenue_amount_52w desc, item_id
            rows between unbounded preceding and current row
        ) as cumulative_revenue,
        sum(revenue_amount_52w) over (partition by store_id) as store_revenue
    from revenue
),

weekly as (
    select
        store_id,
        item_id,
        weeks_ago,
        sum(demand_units) as week_units,
        bool_or(is_on_sale) as was_on_sale
    from window_sales
    group by store_id, item_id, weeks_ago
),

variability as (
    select
        store_id,
        item_id,
        count(*) filter (where was_on_sale) as active_weeks,
        avg(week_units) filter (where was_on_sale) as mean_weekly_units,
        stddev_pop(week_units) filter (where was_on_sale) as sd_weekly_units
    from weekly
    group by store_id, item_id
)

select
    r.store_id,
    r.item_id,
    r.revenue_amount_52w,
    r.revenue_rank,
    r.cumulative_revenue / nullif(r.store_revenue, 0) as cumulative_revenue_share,
    case
        when r.store_revenue = 0 then 'C'
        when (r.cumulative_revenue - r.revenue_amount_52w) / r.store_revenue < 0.80 then 'A'
        when (r.cumulative_revenue - r.revenue_amount_52w) / r.store_revenue < 0.95 then 'B'
        else 'C'
    end as abc_class,
    v.active_weeks,
    v.sd_weekly_units / nullif(v.mean_weekly_units, 0) as weekly_demand_cv,
    case
        when v.active_weeks < 4 or v.mean_weekly_units = 0 then null
        when v.sd_weekly_units / v.mean_weekly_units < 0.5 then 'X'
        when v.sd_weekly_units / v.mean_weekly_units < 1.0 then 'Y'
        else 'Z'
    end as xyz_class
from ranked as r
join variability as v on v.store_id = r.store_id and v.item_id = r.item_id