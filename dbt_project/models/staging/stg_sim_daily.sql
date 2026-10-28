-- Daily output of the simulator: one row per store, product and day.
-- The date is stored as a timestamp in the Parquet files, so we cast it to a date.
-- The day number (0, 1, 2, ...) is dropped: the date says the same thing.

select
    store_id,
    item_id,
    cast(date as date) as date,
    on_sale as is_on_sale,
    opening as opening_units,
    received as received_units,
    demand as demand_units,
    sold as sold_units,
    lost_sales as lost_sales_units,
    expired as expired_units,
    shrunk as shrunk_units,
    cleared as cleared_units,
    record_error as record_error_units,
    count_adjustment as count_adjustment_units,
    end_stock as end_stock_units,
    system_stock as system_stock_units,
    ordered as ordered_units,
    on_order as on_order_units
from {{ source('sim_files', 'daily') }}