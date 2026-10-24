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

## Naming conventions

### Tables (dbt models)
| Layer | Pattern | Examples |
|---|---|---|
| staging | `stg_<source>_<table>` | `stg_m5_sales`, `stg_m5_calendar`, `stg_m5_prices`, `stg_sim_supplier`, `stg_sim_item_supply`, `stg_sim_daily`, `stg_sim_orders` |
| core | `dim_<thing>` (singular), `fct_<events>` | `dim_store`, `fct_inventory_daily`, `fct_deliveries` |
| marts | `mart_<business question>` | `mart_stockout_risk_today` |

- Everything is lowercase `snake_case`. No spaces, no capitals, no abbreviations
  that only I understand.
- One model per file, and the file name equals the model name.
- Folders: `models/staging/`, `models/core/`, `models/marts/`.
- Each folder has one YAML file describing its models and their tests.

### Columns
| Kind | Rule | Examples |
|---|---|---|
| ids | end in `_id` | `store_id`, `item_id`, `purchase_order_id` |
| the day of a daily table | just `date` | `fct_inventory_daily.date` |
| other dates | end in `_date` | `order_date`, `arrival_date`, `as_of_date` |
| quantities | end in `_units` | `demand_units`, `sold_units`, `end_stock_units` |
| prices | end in `_price` | `sell_price` |
| rates and shares | end in `_rate` | `late_rate`, `partial_rate` |
| yes/no flags | start with `is_` or `was_` | `is_on_sale`, `was_cancelled` |

### Meaning of key words
- `demand_units`: what customers wanted to buy (the real M5 sales).
- `sold_units`: what the shelf could actually sell.
- `lost_sales_units`: `demand_units` minus `sold_units`.
- `end_stock_units`: physical stock on the shelf at the end of the day.
- `system_stock_units`: what the computer believes is in stock.

### Tests
Every model gets `unique` and `not_null` tests on its key. Relationships between
facts and dimensions get `relationships` tests (from Day 13).

## Column dictionary

### dim_store (3 rows)
| Column | Type | Meaning | Allowed values |
|---|---|---|---|
| store_id | varchar | Store identifier (key) | CA_1, TX_1, WI_1 |
| state_id | varchar | US state of the store | CA, TX, WI |

### dim_supplier (10 rows)
| Column | Type | Meaning | Allowed values |
|---|---|---|---|
| supplier_id | varchar | Supplier identifier (key) | one of 10 ids |
| cat_id | varchar | The only category this supplier serves | FOODS, HOUSEHOLD, HOBBIES |
| quoted_lead_days | integer | Days promised between order and delivery | FOODS 2, HOUSEHOLD 4, HOBBIES 7 |
| late_rate | double | Share of deliveries that arrive late (1-4 days) | FOODS 0.05-0.10, HOUSEHOLD 0.10-0.15, HOBBIES 0.15-0.25 |
| partial_rate | double | Share of deliveries that arrive incomplete | 0.03-0.07 |

### dim_product (3,049 rows)
| Column | Type | Meaning | Allowed values |
|---|---|---|---|
| item_id | varchar | Product identifier (key) | M5 item ids |
| dept_id | varchar | Department | M5 department ids |
| cat_id | varchar | Category | FOODS, HOUSEHOLD, HOBBIES |
| supplier_id | varchar | The product's supplier | exists in dim_supplier, same category |
| pack_size | integer | Units per pack; orders are whole packs | FOODS 6, HOUSEHOLD 12, HOBBIES 4 |
| moq_packs | integer | Minimum order, in packs | 2 |
| review_days | integer | Days between two stock reviews | FOODS 1, HOUSEHOLD 3, HOBBIES 7 |
| z | double | Service-level factor of the ordering policy | 1.6449 (95%), 1.405 (92%), 1.2816 (90%) |

### dim_date (1,969 rows in the M5 calendar; our project uses 1,941 days)
| Column | Type | Meaning | Allowed values |
|---|---|---|---|
| date | date | Calendar day (key) | 2011-01-29 onward |
| d | varchar | M5 day id | d_1, d_2, ... |
| wm_yr_wk | integer | Walmart week id; joins prices | M5 values |
| weekday, month, year | varchar / integer | Calendar attributes | real calendar values |
| event_name_1, event_type_1 | varchar | Holiday or event on that day | null if none |
| snap_ca, snap_tx, snap_wi | integer | Food-assistance day in that state | 0 or 1 |

### fct_sales (grain: store x product x day)
| Column | Type | Meaning | Allowed values |
|---|---|---|---|
| store_id, item_id, date | | Key | exist in the dimensions |
| demand_units | integer | What customers wanted to buy (real M5 sales) | >= 0 |
| sell_price | double | Price that week | null = not on sale |
| is_on_sale | boolean | A price exists for that week | true / false |

### fct_inventory_daily (grain: store x product x day)
| Column | Type | Meaning | Allowed values |
|---|---|---|---|
| store_id, item_id, date | | Key | exist in the dimensions |
| is_on_sale | boolean | Product is on sale that day | true / false |
| opening_units | integer | Launch delivery (not an order) | >= 0; non-zero only on launch day |
| received_units | integer | Units that arrived from orders | >= 0 |
| demand_units | integer | Customer demand that day | = fct_sales.demand_units |
| sold_units | integer | Units the shelf really sold | 0 to demand_units |
| lost_sales_units | integer | demand_units minus sold_units | >= 0; > 0 = stockout |
| expired_units | integer | Units that expired (FOODS only) | >= 0 |
| shrunk_units | integer | Units lost to theft or damage (the computer does not see them) | >= 0 |
| cleared_units | integer | Stock removed when the product leaves the shelf | >= 0 |
| record_error_units | integer | Error added to the computer's stock | integer, usually -3 to +3 |
| count_adjustment_units | integer | Correction made by a stock count | integer |
| end_stock_units | integer | Physical stock at the end of the day | >= 0 |
| system_stock_units | integer | Stock the computer believes is on the shelf | integer; can differ from the shelf |
| ordered_units | integer | Units ordered that day | >= 0, whole packs, at least the minimum |
| on_order_units | integer | Ordered units not yet arrived | >= 0 |

### fct_purchase_orders (grain: one order placed)
| Column | Type | Meaning | Allowed values |
|---|---|---|---|
| purchase_order_id | varchar | Order identifier (made by us) | unique |
| store_id, item_id | varchar | What and where | exist in the dimensions |
| order_date | date | Day the order was placed | development or live days |
| expected_date | date | Day the delivery is promised | >= order_date |
| ordered_units | integer | Quantity ordered | whole packs, >= 2 packs |
| was_cancelled | boolean | Order cancelled because the product left the shelf | true / false |

### fct_deliveries (grain: one delivery received)
| Column | Type | Meaning | Allowed values |
|---|---|---|---|
| delivery_id | varchar | Delivery identifier (made by us) | unique |
| purchase_order_id | varchar | The order it answers | exists in fct_purchase_orders |
| store_id, item_id | varchar | What and where | exist in the dimensions |
| arrival_date | date | Day the goods arrived | >= order_date |
| delivered_units | integer | Quantity received | 0 to ordered_units |
| days_late | integer | arrival_date minus expected_date | 0 to 4 |