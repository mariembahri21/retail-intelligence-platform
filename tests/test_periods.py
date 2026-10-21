"""Tests on the time periods and the seal of the live test."""
import sys
from datetime import date, timedelta
from pathlib import Path

import duckdb
import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from simulation.periods import (  # noqa: E402
    CONFIG_PATH, SealedPeriodError, assert_not_sealed,
    development_sql, last_development_day, load_periods,
)

ORDER = ["burn_in", "block_a", "gap_1", "block_b", "gap_2", "live_test", "live_replay"]


@pytest.fixture(scope="module")
def periods():
    return load_periods()


def days(period):
    return (period[1] - period[0]).days + 1


def test_periods_are_in_the_expected_order(periods):
    assert list(periods) == ORDER


def test_each_period_starts_the_day_after_the_previous_one_ends(periods):
    for before, after in zip(ORDER, ORDER[1:]):
        assert periods[after][0] == periods[before][1] + timedelta(days=1), (before, after)


def test_periods_cover_exactly_the_project_dates(periods):
    with open(CONFIG_PATH, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    assert periods["burn_in"][0] == date.fromisoformat(cfg["data"]["start_date"])
    assert periods["live_replay"][1] == date.fromisoformat(cfg["data"]["end_date"])


def test_every_period_starts_before_it_ends(periods):
    for name in ORDER:
        assert periods[name][0] <= periods[name][1], name


def test_burn_in_is_28_days_and_gaps_are_7_days(periods):
    assert days(periods["burn_in"]) == 28
    assert days(periods["gap_1"]) == 7
    assert days(periods["gap_2"]) == 7


def test_last_development_day_is_the_day_before_the_live_test(periods):
    assert last_development_day() == date(2015, 6, 30)


def test_development_sql_removes_the_live_test():
    sql = development_sql("d")
    con = duckdb.connect()
    kept = con.sql(
        f"SELECT min(d), max(d), count(*) FROM "
        f"(SELECT unnest(generate_series(DATE '2011-01-29', DATE '2016-05-22', INTERVAL 1 DAY))::DATE AS d) "
        f"WHERE {sql}"
    ).fetchone()
    assert kept[0] == date(2011, 1, 29)
    assert kept[1] == date(2015, 6, 30)


def test_a_range_inside_development_is_allowed():
    assert_not_sealed(date(2014, 7, 8), date(2015, 6, 23))


def test_a_range_touching_the_live_test_is_refused():
    with pytest.raises(SealedPeriodError):
        assert_not_sealed(date(2015, 6, 1), date(2015, 7, 1))
    with pytest.raises(SealedPeriodError):
        assert_not_sealed(date(2016, 5, 1), date(2016, 5, 22))