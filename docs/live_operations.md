# Live operations: the clock and the seal

The platform is meant to "live" day by day: on any given day it may know only what has
happened up to that day. This page explains how that is enforced, what is sealed, and
when the sealed data may be opened.

## The clock

- The clock is one date, stored in `data/state/clock.json` (not in git).
- Without that file, the clock is the last development day, **2015-06-30**.
- Every core fact (`fct_sales`, `fct_inventory_daily`, `fct_purchase_orders`,
  `fct_deliveries`) is loaded only up to the clock date, through the dbt variable
  `as_of_date`.
- Core facts are incremental. A run reloads the last loaded day and everything after it;
  the unique key replaces rows instead of duplicating them. Running the same day twice
  gives the same result (idempotent), and an incremental build gives the same result as
  a full rebuild (checked on development days).
- `fct_deliveries` holds only orders that have already arrived. `fct_purchase_orders` has
  no cancellation flag, because whether an order will be cancelled is only known later.

### Commands (from the project root, virtual environment active)

| Command | Effect |
|---|---|
| `python pipeline/release.py --status` | Show the clock, the last development day and the last day of the data |
| `python pipeline/release.py --days 1 --build` | Move the clock one day forward and load that day with dbt |
| `python pipeline/release.py --through 2015-06-30 --build` | Move the clock to a date and load the days in between |

The clock moves only after dbt succeeded. If dbt fails, nothing moves and the command can
be repeated. The clock only moves forward, never past 2016-05-22, and never into the live
test without `--allow-live`.

To rebuild the core tables from scratch at the current clock date, pass the date
explicitly (the default in `dbt_project.yml` is 2015-06-30):

    dbt build --select core --full-refresh --vars "{as_of_date: '<clock date>'}"

## What is sealed

| Period | Dates | Rule |
|---|---|---|
| Development | 2011-01-29 to 2015-06-30 | Free to analyse, calibrate and train on |
| Live test | 2015-07-01 to 2016-04-30 | Final exam. Never used to decide anything |
| Live replay | 2016-05-01 to 2016-05-22 | The demo: the platform replays these days as if live |

Three layers protect the live test:

1. **The clock.** The core tables contain no day after the clock date. Anything built on
   the core tables (marts, features, models, dashboards) cannot see the future.
2. **The guard in code.** Analysis and training scripts use `development_sql()` and
   `assert_not_sealed()` from `simulation/periods.py`.
3. **The clock command** refuses to enter the live test without an explicit `--allow-live`.

### The limit of the seal

The raw M5 data, the simulator's Parquet files and the staging models contain **all** days,
including the live test. So the seal is complete only if the rule is kept:

> Marts, notebooks, models and dashboards read the core tables only. Nothing reads
> raw, the Parquet files or staging directly (except the core models themselves).

## When the live test may be opened

Only for the final exams, and only in this order:

1. The models are finished and frozen: the code is committed and tagged in git, and the
   model files are saved. Nothing is tuned after this point.
2. Move the clock forward with `--allow-live`, in daily steps, so that each day is
   scored by the models using only what was known that day.
3. Report the results as they are, whatever they are.
4. After the live test has been opened, no decision may be based on it. If something has to
   change, it is documented as a change made after seeing the test.

The live replay is opened last, for the demo.

## Daily routine (once the platform runs live)

1. `python pipeline/release.py --days 1 --build`: load the new day.
2. Score the new day, produce the alerts and recommendations (later phases).
3. Check the dbt tests are green. A red test stops the routine.

## If something goes wrong

- **dbt fails during `--build`:** the clock was not moved. Read the dbt error, fix it, run
  the same command again.
- **"Cannot open file ... used by another process":** close the notebooks that are
  connected to `retail.duckdb`, or restart their kernels. DuckDB allows one writer.
- **Core tables seem to have gone back in time:** someone ran `dbt build --full-refresh`
  without `--vars`, so the default date was used. Rebuild with the command above.