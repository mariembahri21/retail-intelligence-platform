-- Fails if the ABC classes do not follow the revenue ranking:
-- ranks must be 1..n without gaps in each store, the cumulative share must never
-- decrease or exceed 1, and a better-ranked product must never have a worse class.
with ordered as (
    select
        store_id, revenue_rank, abc_class, cumulative_revenue_share,
        lag(abc_class) over (partition by store_id order by revenue_rank) as previous_class,
        lag(cumulative_revenue_share) over (partition by store_id order by revenue_rank) as previous_share
    from {{ ref('dim_product_class') }}
)
select *
from ordered
where cumulative_revenue_share > 1.0000001
   or (previous_share is not null and cumulative_revenue_share < previous_share - 0.0000001)
   or (previous_class = 'B' and abc_class = 'A')
   or (previous_class = 'C' and abc_class in ('A', 'B'))
union all
select store_id, count(*), null, null, null, null
from {{ ref('dim_product_class') }}
group by store_id
having max(revenue_rank) != count(*)