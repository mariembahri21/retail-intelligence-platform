-- Fails if a day is missing or repeated: days must run without gaps.
with span as (
    select count(*) as n_rows, count(distinct date) as n_dates,
           min(date) as first_day, max(date) as last_day
    from {{ ref('stg_m5_calendar') }}
)
select *
from span
where n_rows != n_dates
   or date_diff('day', first_day, last_day) + 1 != n_rows