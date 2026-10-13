# Raw Schema

The `raw` schema in DuckDB (`data/processed/retail.duckdb`) holds the M5 data **exactly as received**. Raw data is never modified: if a later transformation goes wrong, we can rebuild everything from this layer. The only structural change is turning the wide sales file into a long table.

## raw.sales

**Grain:** one row per product, store and day. Only the 3 stores in `config.yaml` are loaded.
**Expected size:** 9,147 series × 1,941 days = 17,754,327 rows.

| Column | Type | Notes |
|---|---|---|
| `item_id` | VARCHAR | Product identifier |
| `dept_id` | VARCHAR | Department |
| `cat_id` | VARCHAR | Category (FOODS, HOUSEHOLD, HOBBIES) |
| `store_id` | VARCHAR | Store identifier |
| `state_id` | VARCHAR | State of the store |
| `d` | VARCHAR | Day id as received (`d_1` to `d_1941`), converted to a date later in staging |
| `units` | INTEGER | Units sold that day |

## raw.calendar

**Grain:** one row per day. 1,969 rows (2011-01-29 to 2016-06-19). Sales stop at `d_1941` (2016-05-22), so the last 28 days have no sales.

| Column | Type | Notes |
|---|---|---|
| `date` | DATE | Calendar date |
| `wm_yr_wk` | INTEGER | Walmart week id, joins to `raw.prices` |
| `weekday` | VARCHAR | Day name |
| `wday` | INTEGER | Day number in the Walmart week (Saturday = 1) |
| `month` | INTEGER | Month number |
| `year` | INTEGER | Year |
| `d` | VARCHAR | Day id, joins to `raw.sales.d` |
| `event_name_1` | VARCHAR | Event name, empty if none |
| `event_type_1` | VARCHAR | Event type, empty if none |
| `event_name_2` | VARCHAR | Second event, rarely filled |
| `event_type_2` | VARCHAR | Second event type |
| `snap_CA` | INTEGER | 1 if SNAP purchases are allowed that day in California, otherwise 0 |
| `snap_TX` | INTEGER | Same for Texas |
| `snap_WI` | INTEGER | Same for Wisconsin |

## raw.prices

**Grain:** one row per product, store and Walmart week. Only the 3 configured stores are loaded. A missing row means the product was not on sale that week.

| Column | Type | Notes |
|---|---|---|
| `store_id` | VARCHAR | Store identifier |
| `item_id` | VARCHAR | Product identifier |
| `wm_yr_wk` | INTEGER | Walmart week id |
| `sell_price` | DECIMAL(8,2) | Price in US dollars |

## Design decisions

- **Raw is never modified.** It is the single source of truth. Cleaning, joins and business logic happen in later layers, so any mistake can be fixed by rebuilding from raw.
- **`raw.sales` is long, not wide.**