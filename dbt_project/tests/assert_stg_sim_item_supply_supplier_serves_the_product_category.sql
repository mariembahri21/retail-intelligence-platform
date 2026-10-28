-- Fails if a product has a supplier from another category.
select p.item_id, p.cat_id as product_category, s.cat_id as supplier_category
from {{ ref('stg_sim_item_supply') }} as p
join {{ ref('stg_sim_supplier') }} as s on s.supplier_id = p.supplier_id
where p.cat_id != s.cat_id