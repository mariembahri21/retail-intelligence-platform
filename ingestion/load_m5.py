"""Load the raw M5 files into the DuckDB warehouse (schema: raw).

Run from the project root:  python ingestion/load_m5.py
"""
import time
from pathlib import Path

import duckdb
import yaml

CONFIG_PATH = Path("config.yaml")
ID_COLUMNS = "item_id, dept_id, cat_id, store_id, state_id"


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def sql_list(values: list[str]) -> str:
    """['CA_1', 'TX_1'] -> "'CA_1', 'TX_1'" for use in a SQL IN (...) clause."""
    return ", ".join(f"'{v}'" for v in values)


def load_sales(con, raw_dir: Path, stores: list[str]) -> None:
    path = (raw_dir / "sales_train_evaluation.csv").as_posix()
    con.execute(f"""
        CREATE OR REPLACE TEMP VIEW sales_wide AS
        SELECT * EXCLUDE (id)
        FROM read_csv('{path}', header = true)
        WHERE store_id IN ({sql_list(stores)})
    """)
    con.execute(f"""
        CREATE OR REPLACE TABLE raw.sales AS
        SELECT {ID_COLUMNS}, d, units::INTEGER AS units
        FROM (
            UNPIVOT sales_wide
            ON COLUMNS(* EXCLUDE ({ID_COLUMNS}))
            INTO NAME d VALUE units
        )
    """)


def load_calendar(con, raw_dir: Path) -> None:
    path = (raw_dir / "calendar.csv").as_posix()
    con.execute(f"""
        CREATE OR REPLACE TABLE raw.calendar AS
        SELECT
            date::DATE        AS date,
            wm_yr_wk::INTEGER AS wm_yr_wk,
            weekday,
            wday::INTEGER     AS wday,
            month::INTEGER    AS month,
            year::INTEGER     AS year,
            d,
            event_name_1,
            event_type_1,
            event_name_2,
            event_type_2,
            snap_CA::INTEGER  AS snap_CA,
            snap_TX::INTEGER  AS snap_TX,
            snap_WI::INTEGER  AS snap_WI
        FROM read_csv('{path}', header = true)
    """)


def load_prices(con, raw_dir: Path, stores: list[str]) -> None:
    path = (raw_dir / "sell_prices.csv").as_posix()
    con.execute(f"""
        CREATE OR REPLACE TABLE raw.prices AS
        SELECT
            store_id,
            item_id,
            wm_yr_wk::INTEGER         AS wm_yr_wk,
            sell_price::DECIMAL(8, 2) AS sell_price
        FROM read_csv('{path}', header = true)
        WHERE store_id IN ({sql_list(stores)})
    """)


def main() -> None:
    config = load_config()
    raw_dir = Path(config["data"]["raw_dir"])
    db_path = Path(config["warehouse"]["path"])
    stores = config["scope"]["stores"]

    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")

    for name, loader in [
        ("raw.sales", lambda: load_sales(con, raw_dir, stores)),
        ("raw.calendar", lambda: load_calendar(con, raw_dir)),
        ("raw.prices", lambda: load_prices(con, raw_dir, stores)),
    ]:
        start = time.time()
        loader()
        rows = con.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
        print(f"{name}: {rows:,} rows loaded in {time.time() - start:.1f}s")

    con.close()


if __name__ == "__main__":
    main()