-- Purchase-order fact: one row per order placed.
-- It records the expectation (what we asked for and when we expected it).
-- What really happened is in fct_deliveries.

select
    purchase_order_id,
    store_id,
    item_id,
    order_date,
    expected_date,
    ordered_units,
    was_cancelled
from {{ ref('stg_sim_orders') }}