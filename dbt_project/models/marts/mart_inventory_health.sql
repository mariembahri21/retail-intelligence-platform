-- Inventory health, one row per store, product and week (weeks start on Monday).
-- Only days on which the product is on sale are counted.
--
-- avg_stock_units    : average end-of-day shelf stock.
-- turnover           : units sold / average stock (how many times the stock was sold in the week).
-- days_of_cover      : average stock / average daily demand (how many days the stock would last).
-- overstock_day_rate : share of days with more than 28 days of cover (4 weeks), where the
--                      daily demand is the average of the last 28 days (fewer at the start).
--                      Stock with no demand at all counts as overstock.
-- waste_rate         : lost units (expired + shrunk + cleared) / (units sold + lost units).
-- stockout_day_rate  : share of days with lost sales.
-- A rate is null when its denominator is 0.

with daily as (
    select
        store_id,
        item_id,
        date,
        is_on_sale,
        end_stock_units,
        sold_units,
        demand_units,
        lost_sales_units,
        is_stockout,
        expired_units + shrunk_units + cleared_units as waste_units,
        avg(demand_units) over (
            partition by store_id, item_id order by date
            rows between 27 preceding and current row
        ) as avg_demand_28d
    from {{ ref('fct_inventory_daily') }}
),

flagged as (
    select
        *,
        end_stock_units > 0 and end_stock_units > 28 * avg_demand_28d as is_overstocked
    from daily
    where is_on_sale
)

select
    store_id,
    item_id,
    date_trunc('week', date)::date as week_start_date,
    count(*) as days_on_sale,
    sum(demand_units) as demand_units,
    sum(sold_units) as sold_units,
    sum(lost_sales_units) as lost_sales_units,
    avg(end_stock_units) as avg_stock_units,
    sum(sold_units) / nullif(avg(end_stock_units), 0) as turnover,
    avg(end_stock_units) / nullif(sum(demand_units) * 1.0 / count(*), 0) as days_of_cover,
    avg(is_overstocked::int) as overstock_day_rate,
    sum(waste_units) as waste_units,
    sum(waste_units) * 1.0 / nullif(sum(sold_units) + sum(waste_units), 0) as waste_rate,
    avg(is_stockout::int) as stockout_day_rate
from flagged
group by store_id, item_id, date_trunc('week', date)::date