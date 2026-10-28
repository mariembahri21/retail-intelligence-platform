-- One row per supplier, with its quoted lead time and reliability.

select
    supplier_id,
    cat_id,
    quoted_lead_days,
    late_rate,
    partial_rate
from {{ ref('stg_sim_supplier') }}