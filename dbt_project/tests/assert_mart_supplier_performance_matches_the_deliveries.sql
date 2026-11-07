-- Fails if the supplier mart loses deliveries or units, has duplicates, or has a rate outside 0 to 1.
select 'deliveries differ' as problem
where (select sum(deliveries) from {{ ref('mart_supplier_performance') }})
   != (select count(*) from {{ ref('fct_deliveries') }})
   or (select sum(delivered_units) from {{ ref('mart_supplier_performance') }})
   != (select sum(delivered_units) from {{ ref('fct_deliveries') }})
union all
select 'duplicate row'
from {{ ref('mart_supplier_performance') }}
group by supplier_id, month_start_date
having count(*) > 1
union all
select 'rate out of range'
from {{ ref('mart_supplier_performance') }}
where otif_rate not between 0 and 1 or on_time_rate not between 0 and 1
   or in_full_rate not between 0 and 1 or fill_rate not between 0 and 1
   or otif_rate > least(on_time_rate, in_full_rate) + 0.0000001