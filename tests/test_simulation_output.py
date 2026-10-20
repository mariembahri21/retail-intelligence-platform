"""Checks on the saved simulation results (the Parquet files).

Run from the project root:
    pytest tests/test_simulation_output.py -v
To check the quick test output instead of the full one (PowerShell):
    $env:SIM_DIR = "data/processed/sim_test"; pytest tests/test_simulation_output.py -v
"""
import os
from pathlib import Path

import duckdb
import pytest
import yaml

SIM_DIR = Path(os.environ.get("SIM_DIR", "data/processed/sim"))


@pytest.fixture(scope="module")
def con():
    if not (SIM_DIR / "daily").exists():
        pytest.skip(f"no simulation output in {SIM_DIR}")
    with open("config.yaml", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    connection = duckdb.connect(config["warehouse"]["path"], read_only=True)
    connection.execute(
        f"CREATE TEMP VIEW daily AS SELECT * FROM read_parquet('{SIM_DIR.as_posix()}/daily/*/*.parquet')"
    )
    connection.execute(
        f"CREATE TEMP VIEW orders AS SELECT * FROM read_parquet('{SIM_DIR.as_posix()}/orders/*/*.parquet')"
    )
    yield connection
    connection.close()


def count(con, sql):
    return con.execute(sql).fetchone()[0]


def test_every_product_has_one_row_per_day(con):
    n_days = count(con, "SELECT COUNT(DISTINCT d) FROM raw.sales")
    wrong = count(con, f"""
        SELECT COUNT(*) FROM (
            SELECT store_id, item_id FROM daily
            GROUP BY store_id, item_id HAVING COUNT(*) <> {n_days}
        )
    """)
    assert wrong == 0


def test_no_duplicate_rows(con):
    total, distinct = con.execute("""
        SELECT COUNT(*), COUNT(DISTINCT (store_id, item_id, day)) FROM daily
    """).fetchone()
    assert total == distinct


def test_demand_is_the_real_m5_sales(con):
    wrong = count(con, """
        SELECT COUNT(*) FROM daily x
        JOIN raw.sales s ON s.store_id = x.store_id AND s.item_id = x.item_id
                        AND s.d = 'd_' || CAST(x.day + 1 AS VARCHAR)
        WHERE x.demand <> s.units
    """)
    assert wrong == 0


def test_no_negative_numbers(con):
    wrong = count(con, """
        SELECT COUNT(*) FROM daily
        WHERE demand < 0 OR opening < 0 OR received < 0 OR sold < 0 OR lost_sales < 0
           OR expired < 0 OR shrunk < 0 OR cleared < 0 OR end_stock < 0
           OR system_stock < 0 OR ordered < 0 OR on_order < 0
    """)
    assert wrong == 0


def test_sold_plus_lost_equals_demand_when_on_sale(con):
    wrong = count(con, """
        SELECT COUNT(*) FROM daily
        WHERE on_sale AND sold + lost_sales <> demand
    """)
    assert wrong == 0


def test_nothing_happens_when_not_on_sale(con):
    wrong = count(con, """
        SELECT COUNT(*) FROM daily
        WHERE NOT on_sale
          AND (sold <> 0 OR lost_sales <> 0 OR received <> 0 OR ordered <> 0
               OR end_stock <> 0 OR system_stock <> 0 OR opening <> 0)
    """)
    assert wrong == 0


def test_stock_balance_for_every_day(con):
    wrong = count(con, """
        SELECT COUNT(*) FROM (
            SELECT end_stock, opening, received, sold, expired, shrunk, cleared,
                   LAG(end_stock) OVER (PARTITION BY store_id, item_id ORDER BY day) AS yesterday
            FROM daily
        )
        WHERE yesterday IS NOT NULL
          AND end_stock <> yesterday + opening + received - sold - expired - shrunk - cleared
    """)
    assert wrong == 0


def test_orders_respect_pack_size_and_minimum_order(con):
    wrong = count(con, """
        SELECT COUNT(*) FROM orders o
        JOIN sim.item_supply i USING (item_id)
        WHERE o.ordered_qty % i.pack_size <> 0
           OR o.ordered_qty < i.moq_packs * i.pack_size
    """)
    assert wrong == 0


def test_order_dates_and_quantities_make_sense(con):
    wrong = count(con, """
        SELECT COUNT(*) FROM orders
        WHERE delivered_qty > ordered_qty OR delivered_qty < 1
           OR arrival_day < expected_day OR late_days < 0 OR late_days > 4
           OR expected_day <= order_day
    """)
    assert wrong == 0


def test_orders_table_matches_the_daily_table(con):
    in_daily = count(con, "SELECT COALESCE(SUM(ordered), 0) FROM daily")
    in_orders = count(con, "SELECT COALESCE(SUM(ordered_qty), 0) FROM orders")
    assert in_daily == in_orders