-- One row per product: its supplier and its ordering terms.

select
    item_id,
    dept_id,
    cat_id,
    supplier_id,
    pack_size,
    moq_packs,
    review_days,
    service_level,
    z
from {{ source('sim', 'item_supply') }}