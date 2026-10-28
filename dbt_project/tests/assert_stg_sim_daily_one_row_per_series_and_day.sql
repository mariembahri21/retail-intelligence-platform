-- Fails if a (store, product, day) appears twice.
select store_id, item_id, date, count(*) as n
from {{ ref('stg_sim_daily') }}
group by store_id, item_id, date
having count(*) > 1