-- One row per store, product and day, as received from M5.
-- Staging only renames columns; the date comes later, in the core layer.

select
    store_id,
    item_id,
    dept_id,
    cat_id,
    state_id,
    d,
    units as demand_units
from {{ source('raw', 'sales') }}