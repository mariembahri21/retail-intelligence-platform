-- One row per store.

select distinct
    store_id,
    state_id
from {{ ref('stg_m5_sales') }}