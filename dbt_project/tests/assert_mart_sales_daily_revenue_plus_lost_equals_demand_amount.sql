-- Fails if revenue + lost revenue is not the value of the demand.
select *
from {{ ref('mart_sales_daily') }}
where abs(coalesce(revenue, 0) + coalesce(lost_revenue, 0) - coalesce(demand_amount, 0)) > 0.01