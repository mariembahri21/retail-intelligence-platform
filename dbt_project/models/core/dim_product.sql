-- One row per product, with its category, supplier and ordering terms.

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
from {{ ref('stg_sim_item_supply') }}