-- One row per store, product and Walmart week.
-- A missing row means the product was not on sale that week.

select
    store_id,
    item_id,
    wm_yr_wk,
    sell_price
from {{ source('raw', 'prices') }}