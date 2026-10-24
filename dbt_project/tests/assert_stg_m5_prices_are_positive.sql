-- Fails if a price is zero or negative.
select *
from {{ ref('stg_m5_prices') }}
where sell_price <= 0