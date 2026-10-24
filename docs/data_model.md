# Data model

## Layers

| Layer | Prefix | Role |
|---|---|---|
| raw | (none) | Data as loaded: M5 tables and the simulator's Parquet output |
| staging | `stg_` | One model per raw table; clean names and types, no business logic |
| core | `dim_`, `fct_` | Dimensions and facts |
| marts | `mart_` | Business-ready tables for dashboards and models |

Each layer reads only from the previous one.

## Grain of every table

| Table | One row is... | Key | Source |
|---|---|---|---|
| `dim_date` | one calendar day | `date` | M5 calendar |
| `dim_store` | one store | `store_id` | M5 sales |
| `dim_product` | one product (item) | `item_id` | M5 sales + `sim.item_supply` |
| `dim_supplier` | one supplier | `supplier_id` | `sim.supplier` |
| `fct_sales` | one store x product x day | `store_id, item_id, date` | M5 sales and prices |
| `fct_inventory_daily` | one store x product x day | `store_id, item_id, date` | simulator `daily` output |
| `fct_purchase_orders` | one order placed | `store_id, item_id, order_date` | simulator `orders` output |
| `fct_deliveries` | one delivery received (one per delivered order) | same as the order | simulator `orders` output |

### Rules

- `fct_sales` and `fct_inventory_daily` share a grain, so they join one-to-one.
  Their link: `fct_sales.demand_units` is the demand the simulator received;
  `fct_inventory_daily.sold_units` is what the shelf could really sell;
  the difference is `lost_sales_units`.
- Purchase orders and deliveries are events with their own grain. They are never
  joined to a daily table without aggregating to day level first (fan-out).
- A cancelled order (product left the shelf) has no delivery.
- The launch delivery (`opening`) is not an order: it appears only in
  `fct_inventory_daily`.
- Dimensions describe; facts measure. Supplier traits (lead time, late rate)
  live in `dim_supplier`; the lateness of one delivery lives in `fct_deliveries`.
- Planned later: `fct_demand_forecast`, `fct_stockout_risk`, `fct_recommendations`
  (grain: store x product x day, plus a run or model version).