-- Fails if a delivery breaks the rules: late 0-4 days, no more than ordered,
-- fill rate between 0 and 1, OTIF only when on time and in full.
select *
from {{ ref('fct_deliveries') }}
where days_late not between 0 and 4
   or delivered_units > ordered_units
   or fill_rate <= 0 or fill_rate > 1
   or is_otif != (is_on_time and is_in_full)
   or actual_lead_days != promised_lead_days + days_late