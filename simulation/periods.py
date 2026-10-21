"""Time periods of the project (read from config.yaml) and the seal on the live test.

The live test is the final exam. Code that analyses, calibrates or trains must
only look at development days, so it filters with development_sql() or checks
its date range with assert_not_sealed().
"""
from datetime import date, timedelta
from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


class SealedPeriodError(Exception):
    """Raised when code tries to use days from the sealed live test."""


def load_periods(path=CONFIG_PATH):
    """Return {name: (first_day, last_day)} with real date objects."""
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return {
        name: (date.fromisoformat(first), date.fromisoformat(last))
        for name, (first, last) in cfg["periods"].items()
    }


def last_development_day(path=CONFIG_PATH):
    """The day before the live test starts."""
    return load_periods(path)["live_test"][0] - timedelta(days=1)


def development_sql(column="date", path=CONFIG_PATH):
    """SQL condition that keeps only development days (never the live test)."""
    return f"{column} <= DATE '{last_development_day(path)}'"


def assert_not_sealed(first_day, last_day, path=CONFIG_PATH):
    """Stop with an error if the date range touches the sealed live test."""
    if last_day > last_development_day(path):
        raise SealedPeriodError(
            f"{first_day} to {last_day} touches the sealed live test "
            f"(it starts {load_periods(path)['live_test'][0]}). "
            "Use development days only."
        )