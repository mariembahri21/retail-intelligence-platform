"""Data quality checks on the raw layer of the DuckDB warehouse.
"""
from pathlib import Path

import duckdb
import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
EXPECTED_SALES_DAYS = 1941   # d_1 ... d_1941 (2011-01-29 to 2016-05-22)
EXPECTED_CALENDAR_DAYS = 1969   # calendar runs 28 days past the last sale


@pytest.fixture(scope="module")
def config():
    with open(ROOT / "config.yaml") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def con(config):
    db_path = ROOT / config["warehouse"]["path"]
    if not db_path.exists():
        pytest.skip("Warehouse not built yet: run python ingestion/load_m5.py")
    connection = duckdb.connect(str(db_path), read_only=True)
    yield connection
    connection.close()


def scalar(con, sql):
    """Run a query that returns one value and give back that value."""
    return con.execute(sql).fetchone()[0]


# ---------- raw.sales ----------
def test_sales_has_expected_number_of_days(con):
    assert scalar(con, "SELECT COUNT(DISTINCT d) FROM raw.sales") == EXPECTED_SALES_DAYS


def test_sales_row_count_is_series_times_days(con):
    series = scalar(con, "SELECT COUNT(*) FROM (SELECT DISTINCT item_id, store_id FROM raw.sales)")
    rows = scalar(con, "SELECT COUNT(*) FROM raw.sales")
    assert rows == series * EXPECTED_SALES_DAYS


def test_sales_only_contains_configured_stores(con, config):
    stores = {r[0] for r in con.execute("SELECT DISTINCT store_id FROM raw.sales").fetchall()}
    assert stores == set(config["scope"]["stores"])


def test_sales_has_no_duplicate_rows(con):
    duplicates = scalar(con, """
        SELECT COUNT(*) FROM (
            SELECT item_id, store_id, d FROM raw.sales
            GROUP BY item_id, store_id, d HAVING COUNT(*) > 1
        )""")
    assert duplicates == 0


def test_sales_key_columns_have_no_nulls(con):
    nulls = scalar(con, """
        SELECT COUNT(*) FROM raw.sales
        WHERE item_id IS NULL OR store_id IS NULL OR d IS NULL OR units IS NULL""")
    assert nulls == 0


def test_sales_units_are_never_negative(con):
    assert scalar(con, "SELECT COUNT(*) FROM raw.sales WHERE units < 0") == 0


def test_every_sales_day_exists_in_calendar(con):
    orphans = scalar(con, """
        SELECT COUNT(*) FROM (SELECT DISTINCT d FROM raw.sales) s
        LEFT JOIN raw.calendar c USING (d) WHERE c.date IS NULL""")
    assert orphans == 0


def test_every_sales_series_has_a_price(con):
    missing = scalar(con, """
        SELECT COUNT(*) FROM (SELECT DISTINCT item_id, store_id FROM raw.sales) s
        LEFT JOIN (SELECT DISTINCT item_id, store_id FROM raw.prices) p
        USING (item_id, store_id) WHERE p.item_id IS NULL""")
    assert missing == 0


# ---------- raw.calendar ----------
def test_calendar_has_expected_number_of_days(con):
    assert scalar(con, "SELECT COUNT(*) FROM raw.calendar") == EXPECTED_CALENDAR_DAYS


def test_calendar_dates_are_unique(con):
    assert scalar(con, "SELECT COUNT(*) - COUNT(DISTINCT date) FROM raw.calendar") == 0


def test_calendar_has_no_gaps(con):
    # If every day is present, rows = last date - first date + 1.
    assert scalar(con, """
        SELECT COUNT(*) = DATEDIFF('day', MIN(date), MAX(date)) + 1
        FROM raw.calendar""") is True


def test_snap_flags_are_zero_or_one(con):
    bad = scalar(con, """
        SELECT COUNT(*) FROM raw.calendar
        WHERE snap_CA NOT IN (0, 1) OR snap_TX NOT IN (0, 1) OR snap_WI NOT IN (0, 1)""")
    assert bad == 0


# ---------- raw.prices ----------
def test_prices_only_contains_configured_stores(con, config):
    stores = {r[0] for r in con.execute("SELECT DISTINCT store_id FROM raw.prices").fetchall()}
    assert stores <= set(config["scope"]["stores"])


def test_prices_have_no_duplicates(con):
    duplicates = scalar(con, """
        SELECT COUNT(*) FROM (
            SELECT store_id, item_id, wm_yr_wk FROM raw.prices
            GROUP BY store_id, item_id, wm_yr_wk HAVING COUNT(*) > 1
        )""")
    assert duplicates == 0


def test_prices_are_positive(con):
    assert scalar(con, "SELECT COUNT(*) FROM raw.prices WHERE sell_price IS NULL OR sell_price <= 0") == 0


def test_every_price_week_exists_in_calendar(con):
    orphans = scalar(con, """
        SELECT COUNT(*) FROM raw.prices p
        LEFT JOIN (SELECT DISTINCT wm_yr_wk FROM raw.calendar) c USING (wm_yr_wk)
        WHERE c.wm_yr_wk IS NULL""")
    assert orphans == 0