# Reconciliation

The warehouse holds the same facts in several places. This page records the checks
that prove the numbers agree. Every check is an automatic dbt test: if one breaks,
`dbt build` fails.

## What is checked

| Check | dbt test | What it proves |
|---|---|---|
| Staging keeps every row | `assert_stg_m5_sales_row_count_is_series_times_days`, `assert_stg_sim_daily_has_as_many_rows_as_m5_sales` | No sales row was lost or duplicated while cleaning |
| Simulator demand = real M5 sales | `assert_stg_sim_daily_demand_equals_m5_sales` | The synthetic side is tied to the real data, day by day |
| `fct_sales` keeps every row | `assert_fct_sales_keeps_every_sales_row` | The joins with calendar and prices lost nothing |
| Same rows in both daily facts | `assert_fct_inventory_daily_has_as_many_rows_as_fct_sales` | Sales and inventory join one to one |
| Same demand in both daily facts | `assert_fct_inventory_daily_demand_equals_fct_sales` | No join or simulator bug |
| Sold + lost = demand | `assert_fct_inventory_daily_stockout_means_lost_sales` | Stockouts are defined by lost sales, nothing else |
| Deliveries = stock received | `assert_fct_deliveries_match_received_units` | Every unit that entered the stock came from a delivery |
| Orders = units ordered in stock | `assert_fct_purchase_orders_match_ordered_units` | The order table and the daily stock agree |

## Numbers (from the full run)

| Measure | Value |
|---|---|
| Rows in `fct_sales` | 17754327 |
| Rows in `fct_inventory_daily` | 17754327 |
| Orders placed | 1023759 |
| Orders cancelled (product left the shelf) | 0 |
| Deliveries | 1021489 |
| Orders still on the way when the data ends (orders_placed - orders_cancelled - deliveries) | 1023759 - 0 - 1021489 |
| Units delivered / units received in stock | 17904775 / 17904775 |

Order flow: orders placed = cancelled + delivered + still on the way.

## Supply-chain measures by category

| cat_id    | deliveries | pct_on_time | pct_in_full | pct_otif | avg_lead_days |
| --------- | ---------- | ----------- | ----------- | -------- | ------------- |
| FOODS     |     786657 |        91.9 |        94.1 |     86.5 |           2.2 |
| HOBBIES   |      90358 |        79.1 |        95.8 |     75.8 |           7.5 |
| HOUSEHOLD |     144474 |        88.1 |        94.1 |     82.8 |           4.3 |


## Definitions

- Stockout: a day with `lost_sales_units > 0`.
- On time: `days_late = 0`. In full: delivered units are at least the ordered units.
  OTIF is both together, with no tolerance.
- `fct_deliveries` excludes cancelled orders and orders that would arrive after the
  last simulated day.

## Known limits
- M5 has no costs, so there is no inventory value in the warehouse.

## View versus table
- Same answer from both: True
- Rows in the table: 17,754,327