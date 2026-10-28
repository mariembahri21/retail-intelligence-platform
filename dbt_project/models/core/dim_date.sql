-- One row per calendar day, with attributes to slice reports by.

select
    date,
    d,
    wm_yr_wk,
    year,
    quarter(date) as quarter,
    month,
    weekofyear(date) as week_of_year,
    weekday,
    wday,
    dayofweek(date) in (0, 6) as is_weekend,
    (event_name_1 is not null or event_name_2 is not null) as is_event_day,
    event_name_1,
    event_type_1,
    event_name_2,
    event_type_2,
    snap_ca,
    snap_tx,
    snap_wi
from {{ ref('stg_m5_calendar') }}