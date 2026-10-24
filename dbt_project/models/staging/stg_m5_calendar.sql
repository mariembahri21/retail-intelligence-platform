-- One row per calendar day. Blank event fields become real nulls.

select
    date,
    d,
    wm_yr_wk,
    weekday,
    wday,
    month,
    year,
    nullif(event_name_1, '') as event_name_1,
    nullif(event_type_1, '') as event_type_1,
    nullif(event_name_2, '') as event_name_2,
    nullif(event_type_2, '') as event_type_2,
    snap_ca,
    snap_tx,
    snap_wi
from {{ source('raw', 'calendar') }}