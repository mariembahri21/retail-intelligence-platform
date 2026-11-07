"""The clock of the platform: it decides which days the warehouse may know.

The clock is a date, stored in data/state/clock.json. Every core fact is loaded only
up to that date (the dbt variable as_of_date). Moving the clock forward is the only
way to let the platform see new days.

Usage (from the project root):
    python pipeline/release.py --status
    python pipeline/release.py --days 1 --build
    python pipeline/release.py --through 2015-06-30 --build

Rules:
  - the clock only moves forward (asking for the same date again is allowed and changes nothing);
  - it never goes past the last day of the data (config.yaml, data.end_date);
  - it does not cross into the sealed live test unless you add --allow-live
    (only for the final exams, see docs/live_operations.md);
  - with --build, the clock is saved only after dbt succeeded, so a failed run can be repeated.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CLOCK_PATH = ROOT / "data" / "state" / "clock.json"
CONFIG_PATH = ROOT / "config.yaml"
DBT_DIR = ROOT / "dbt_project"


class ClockError(Exception):
    """The clock was asked to do something it must not do."""


def load_config(config_path=CONFIG_PATH):
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def last_development_day(config):
    """The day before the live test starts."""
    return date.fromisoformat(config["periods"]["live_test"][0]) - timedelta(days=1)


def read_clock(clock_path=CLOCK_PATH, config_path=CONFIG_PATH):
    """Current clock date. Without a clock file, it is the last development day."""
    if clock_path.exists():
        return date.fromisoformat(json.loads(clock_path.read_text(encoding="utf-8"))["as_of_date"])
    return last_development_day(load_config(config_path))


def write_clock(as_of, clock_path=CLOCK_PATH):
    """Save the clock. The file appears only when complete."""
    clock_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = clock_path.with_name(clock_path.name + ".tmp")
    tmp.write_text(json.dumps({"as_of_date": as_of.isoformat()}), encoding="utf-8")
    os.replace(tmp, clock_path)


def new_clock_date(current, days, through, config, allow_live=False):
    """The date the clock should move to, after checking every rule."""
    if (days is None) == (through is None):
        raise ClockError("Give exactly one of --days and --through.")
    if days is not None:
        if days < 1:
            raise ClockError("--days must be at least 1.")
        target = current + timedelta(days=days)
    else:
        target = through

    end_date = date.fromisoformat(str(config["data"]["end_date"]))
    if target < current:
        raise ClockError(f"The clock only moves forward: it is at {current}, not {target}.")
    if target > end_date:
        raise ClockError(f"{target} is after the last day of the data ({end_date}).")
    last_dev = last_development_day(config)
    if target > last_dev and not allow_live:
        raise ClockError(
            f"{target} is inside the sealed live test (it starts {last_dev + timedelta(days=1)}). "
            "Add --allow-live only for the final exams."
        )
    return target


def run_dbt_build(as_of, dbt_dir=DBT_DIR):
    """Build the core tables up to the clock date. Raises ClockError if dbt fails."""
    dbt = shutil.which("dbt")
    if dbt is None:
        raise ClockError("dbt was not found. Activate the virtual environment first.")
    command = [dbt, "build", "--select", "core", "--profiles-dir", ".",
               "--vars", json.dumps({"as_of_date": as_of.isoformat()})]
    result = subprocess.run(command, cwd=dbt_dir)
    if result.returncode != 0:
        raise ClockError("dbt build failed. The clock was not moved.")


def release(days=None, through=None, build=False, allow_live=False,
            clock_path=CLOCK_PATH, config_path=CONFIG_PATH, build_fn=None):
    """Move the clock forward and (optionally) load the new days. Returns the new date."""
    config = load_config(config_path)
    current = read_clock(clock_path, config_path)
    target = new_clock_date(current, days, through, config, allow_live)
    if build:
        (build_fn or run_dbt_build)(target)       # the clock moves only if this succeeds
    write_clock(target, clock_path)
    return target


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Move the platform clock forward.")
    parser.add_argument("--days", type=int, help="move forward by N days")
    parser.add_argument("--through", type=date.fromisoformat, help="move forward to this date (YYYY-MM-DD)")
    parser.add_argument("--build", action="store_true", help="run dbt build for the new days")
    parser.add_argument("--allow-live", action="store_true", help="allow entering the sealed live test")
    parser.add_argument("--status", action="store_true", help="show the clock and exit")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    config = load_config()
    if args.status:
        print(f"Clock date:           {read_clock()}")
        print(f"Last development day: {last_development_day(config)}")
        print(f"Last day of the data: {config['data']['end_date']}")
        return 0
    try:
        before = read_clock()
        after = release(args.days, args.through, args.build, args.allow_live)
    except ClockError as error:
        print(f"Clock not moved: {error}")
        return 1
    print(f"Clock: {before} -> {after}")
    if not args.build:
        print("Core tables were not rebuilt. Run again with --build to load the new days.")
    return 0


if __name__ == "__main__":
    sys.exit(main())