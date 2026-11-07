-- Supplier performance, one row per supplier and month (month of arrival).
-- Only deliveries that have arrived are counted (cancelled orders and orders still on the
-- road have no delivery).
--
-- on_time_rate : share of deliveries that arrived on the promised day.
-- in_full_rate : share of deliveries that brought everything that was ordered.
-- otif_rate    : on time AND in full.
-- fill_rate    : units delivered / units ordered.
-- avg_days_late: average of days_late (0 for on-time deliveries).
-- lead_time_sd : standard deviation of the real lead time in days (null with one delivery).

select
    p.supplier_id,
    date_trunc('month', d.arrival_date)::date as month_start_date,
    count(*) as deliveries,
    sum(d.ordered_units) as ordered_units,
    sum(d.delivered_units) as delivered_units,
    sum(d.delivered_units) * 1.0 / sum(d.ordered_units) as fill_rate,
    avg(d.is_on_time::int) as on_time_rate,
    avg(d.is_in_full::int) as in_full_rate,
    avg(d.is_otif::int) as otif_rate,
    avg(d.days_late) as avg_days_late,
    avg(d.actual_lead_days) as avg_lead_days,
    stddev_samp(d.actual_lead_days) as lead_time_sd
from {{ ref('fct_deliveries') }} as d
join {{ ref('dim_product') }} as p on p.item_id = d.item_id
group by p.supplier_id, date_trunc('month', d.arrival_date)::date