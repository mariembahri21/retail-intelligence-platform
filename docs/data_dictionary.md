# Data Dictionary

This document describes the three M5 files used by the project. The raw files are in `data/raw/` and are not stored in the repository (see `docs/data_sources.md`).

## sales_train_evaluation.csv

Daily unit sales. **Grain:** one row per product in each store (item × store). Days are stored as columns (wide format).

| Column | Meaning | Example |
|---|---|---|
| `id` | Unique id of the series (item + store + file type) | `HOBBIES_1_001_CA_1_evaluation` |
| `item_id` | Product identifier | `HOBBIES_1_001` |
| `dept_id` | Department of the product | `HOBBIES_1` |
| `cat_id` | Category of the product: FOODS, HOUSEHOLD or HOBBIES | `HOBBIES` |
| `store_id` | Store identifier | `CA_1` |
| `state_id` | US state of the store (CA, TX or WI) | `CA` |
| `d_1` … `d_1941` | Units sold on that day. The day number is converted to a date through `calendar.csv` | `0`, `2`, `1` |

Scope of this project: 3 stores (`CA_1`, `TX_1`, `WI_1`) × about 3,049 products = 9,147 series.

## calendar.csv

Calendar information. **Grain:** one row per day.

| Column | Meaning | Example |
|---|---|---|
| `date` | Calendar date | `2011-01-29` |
| `wm_yr_wk` | Walmart week id. It links a day to the weekly prices in `sell_prices.csv` | `11101` |
| `weekday` | Name of the day of the week | `Saturday` |
| `wday` | Number of the day inside the Walmart week. The week starts on Saturday, so Saturday = 1 | `1` |
| `month` | Month number | `1` |
| `year` | Year | `2011` |
| `d` | Day id used as the column name in the sales file | `d_1` |
| `event_name_1` | Name of the special event of the day, empty if none | `SuperBowl` |
| `event_type_1` | Type of that event: Sporting, Cultural, National or Religious, empty if none | `Sporting` |
| `event_name_2` | Name of a second event on the same day. Very rarely filled | (usually empty) |
| `event_type_2` | Type of the second event | (usually empty) |
| `snap_CA` | 1 if SNAP food-assistance purchases are allowed that day in California, otherwise 0 | `0` |
| `snap_TX` | Same flag for Texas | `0` |
| `snap_WI` | Same flag for Wisconsin | `0` |

The calendar has more days than the sales file: sales stop at `d_1941` (2016-05-22).

## sell_prices.csv

Weekly selling prices. **Grain:** one row per product, store and Walmart week.

| Column | Meaning | Example |
|---|---|---|
| `store_id` | Store identifier | `CA_1` |
| `item_id` | Product identifier | `HOBBIES_1_001` |
| `wm_yr_wk` | Walmart week id (see `calendar.csv`) | `11325` |
| `sell_price` | Selling price of the product that week, in US dollars | `9.58` |

## Important notes from exploration

- **A missing price row means the product was not on sale** in that store that week. 64% of the series start after day 1, and about 20% of all item-days happen before the product's first price, so the product was not yet on sale. No units are sold on those days.
- **A zero in the sales data does not always mean "no demand".** It can mean: no customer wanted the product, the product was not yet on sale, the store was closed (for example on Christmas Day), or the shelf was empty (a stockout).
- **Demand is intermittent.** When products are on sale, about 59.5% of item-days still have zero sales (HOBBIES 71.5%, HOUSEHOLD 64.4%, FOODS 52.0%, using the series average).
- **Event columns are empty on days without an event.** SNAP flags are stored per state and only the flag matching the store's state applies to that store.