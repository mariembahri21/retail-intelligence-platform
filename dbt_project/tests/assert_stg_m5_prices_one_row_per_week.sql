-- Fails if a (store, product, week) has more than one price.
select store_id, item_id, wm_yr_wk, count(*) as n
from {{ ref('stg_m5_prices') }}
group by store_id, item_id, wm_yr_wk
having count(*) > 1