-- Demand fact: one row per store, product and day (the real M5 sales).
-- Left joins keep every sales row. is_on_sale is true when a price exists
-- for that store, product and week; days before a product is listed are
-- not real zeros, and this flag lets us tell them apart.

select
    s.store_id,
    s.item_id,
    c.date,
    s.demand_units,
    p.sell_price,
    (p.sell_price is not null) as is_on_sale,
    s.demand_units * p.sell_price as demand_amount
from {{ ref('stg_m5_sales') }} as s
join {{ ref('stg_m5_calendar') }} as c on c.d = s.d
left join {{ ref('stg_m5_prices') }} as p
    on p.store_id = s.store_id
   and p.item_id = s.item_id
   and p.wm_yr_wk = c.wm_yr_wk