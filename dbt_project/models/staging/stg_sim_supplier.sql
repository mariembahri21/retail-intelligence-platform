-- One row per supplier. The simulator calls the category column "category";
-- we use cat_id everywhere.

select
    supplier_id,
    category as cat_id,
    quoted_lead_days,
    late_rate,
    partial_rate
from {{ source('sim', 'supplier') }}