"""Tests on the platform clock (pipeline/release.py) and on the daily loop."""
import json
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from pipeline import release as clock  # noqa: E402
import fixture_warehouse  # noqa: E402

CONFIG = ROOT / "config.yaml"


@pytest.fixture()
def clock_file(tmp_path):
    return tmp_path / "state" / "clock.json"


def move(clock_file, **kwargs):
    return clock.release(clock_path=clock_file, config_path=CONFIG, **kwargs)


def test_without_a_clock_file_the_clock_is_the_last_development_day(clock_file):
    assert clock.read_clock(clock_file, CONFIG) == date(2015, 6, 30)


def test_clock_is_saved_and_read_back(clock_file):
    clock.write_clock(date(2012, 5, 17), clock_file)
    assert clock.read_clock(clock_file, CONFIG) == date(2012, 5, 17)
    assert json.loads(clock_file.read_text()) == {"as_of_date": "2012-05-17"}


def test_days_moves_the_clock_forward(clock_file):
    clock.write_clock(date(2012, 5, 17), clock_file)
    assert move(clock_file, days=3) == date(2012, 5, 20)
    assert clock.read_clock(clock_file, CONFIG) == date(2012, 5, 20)


def test_through_moves_the_clock_to_that_date(clock_file):
    clock.write_clock(date(2012, 5, 17), clock_file)
    assert move(clock_file, through=date(2012, 6, 1)) == date(2012, 6, 1)


def test_asking_for_the_same_date_again_changes_nothing(clock_file):
    clock.write_clock(date(2012, 5, 17), clock_file)
    assert move(clock_file, through=date(2012, 5, 17)) == date(2012, 5, 17)
    assert clock.read_clock(clock_file, CONFIG) == date(2012, 5, 17)


def test_the_clock_never_goes_back(clock_file):
    clock.write_clock(date(2012, 5, 17), clock_file)
    with pytest.raises(clock.ClockError):
        move(clock_file, through=date(2012, 5, 16))
    assert clock.read_clock(clock_file, CONFIG) == date(2012, 5, 17)


def test_the_clock_needs_exactly_one_of_days_and_through(clock_file):
    with pytest.raises(clock.ClockError):
        move(clock_file)
    with pytest.raises(clock.ClockError):
        move(clock_file, days=1, through=date(2012, 6, 1))
    with pytest.raises(clock.ClockError):
        move(clock_file, days=0)


def test_the_clock_refuses_to_enter_the_sealed_live_test(clock_file):
    clock.write_clock(date(2015, 6, 29), clock_file)
    with pytest.raises(clock.ClockError, match="sealed"):
        move(clock_file, days=2)
    assert clock.read_clock(clock_file, CONFIG) == date(2015, 6, 29)


def test_the_live_test_can_be_entered_only_on_purpose(clock_file):
    clock.write_clock(date(2015, 6, 29), clock_file)
    assert move(clock_file, days=2, allow_live=True) == date(2015, 7, 1)


def test_the_clock_never_goes_past_the_end_of_the_data(clock_file):
    clock.write_clock(date(2016, 5, 21), clock_file)
    assert move(clock_file, days=1, allow_live=True) == date(2016, 5, 22)
    with pytest.raises(clock.ClockError, match="last day"):
        move(clock_file, days=1, allow_live=True)


def test_the_clock_does_not_move_when_the_build_fails(clock_file):
    clock.write_clock(date(2012, 5, 17), clock_file)

    def failing_build(as_of):
        raise clock.ClockError("dbt build failed")

    with pytest.raises(clock.ClockError):
        move(clock_file, days=3, build=True, build_fn=failing_build)
    assert clock.read_clock(clock_file, CONFIG) == date(2012, 5, 17)


# ---------- the daily loop, on a tiny fake warehouse ----------

DAILY_TABLES = ("fct_sales", "fct_inventory_daily")
N_SERIES = len(fixture_warehouse.STORES) * len(fixture_warehouse.ITEMS)


@pytest.fixture(scope="module")
def project(tmp_path_factory):
    """A throwaway project: the real dbt project on top of a fake warehouse."""
    if shutil.which("dbt") is None:
        pytest.skip("dbt is not installed in this environment")
    root = tmp_path_factory.mktemp("loop")
    fixture_warehouse.build(root)
    shutil.copytree(ROOT / "dbt_project", root / "dbt_project",
                    ignore=shutil.ignore_patterns("target", "logs", "dbt_packages", ".user.yml"))
    shutil.copy(CONFIG, root / "config.yaml")
    dbt = shutil.which("dbt")
    result = subprocess.run([dbt, "run", "--select", "staging", "--profiles-dir", "."],
                            cwd=root / "dbt_project", capture_output=True, text=True)
    assert result.returncode == 0, result.stdout[-2000:]       # staging views must exist first
    return root


def snapshot(root):
    con = duckdb.connect(str(root / "data" / "processed" / "retail.duckdb"), read_only=True)
    try:
        out = {}
        for table in ("fct_sales", "fct_inventory_daily", "fct_purchase_orders", "fct_deliveries"):
            out[table] = con.execute(
                f"SELECT count(*), md5(string_agg(md5(t::varchar), '' ORDER BY md5(t::varchar))) FROM main.{table} t"
            ).fetchone()
        return out
    finally:
        con.close()


def test_releasing_days_adds_exactly_those_days_and_a_repeat_changes_nothing(project):
    clock_file = project / "data" / "state" / "clock.json"
    dbt_dir = project / "dbt_project"
    config = project / "config.yaml"

    def release(**kwargs):
        return clock.release(clock_path=clock_file, config_path=config, build=True,
                             build_fn=lambda as_of: clock.run_dbt_build(as_of, dbt_dir), **kwargs)

    clock.write_clock(date(2011, 3, 1), clock_file)
    clock.run_dbt_build(date(2011, 3, 1), dbt_dir)
    before = snapshot(project)
    assert before["fct_inventory_daily"][0] == N_SERIES * 32          # 2011-01-29 .. 2011-03-01

    assert release(days=3) == date(2011, 3, 4)
    after = snapshot(project)
    for table in DAILY_TABLES:
        assert after[table][0] - before[table][0] == N_SERIES * 3     # exactly 3 new days
    assert clock.read_clock(clock_file, config) == date(2011, 3, 4)

    assert release(through=date(2011, 3, 4)) == date(2011, 3, 4)      # the same days again
    assert snapshot(project) == after                                  # nothing changed, not even a value