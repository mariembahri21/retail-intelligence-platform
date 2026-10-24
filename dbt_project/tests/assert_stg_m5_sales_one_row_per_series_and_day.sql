-- Fails if a (store, product, day) appears twice.
select store_id, item_id, d, count(*) as n
from {{ ref('stg_m5_sales') }}
group by store_id, item_id, d
having count(*) > 1