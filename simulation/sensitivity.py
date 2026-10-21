"""Sensitivity test: do our findings survive if every lead time is longer?

Runs a random sample of products twice on DEVELOPMENT days only (never the sealed
live test): once with the normal lead times, once with every lead time longer by
EXTRA_DAYS. Prints lost demand, stockout days and the 7-day label rate per
category and period.

Usage (from the project root):
    python simulation/sensitivity.py
    python simulation/sensitivity.py --extra-days 2 --per-category 40
"""
import argparse
import sys
from collections import defaultdict
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from simulation.periods import assert_not_sealed, last_development_day, load_periods  # noqa: E402
from simulation.run_simulation import (  # noqa: E402
    LAUNCH_SQL, SERIES_SQL, TERMS_SQL, load_config, simulate_chunk,
)


def parse_args():
    parser = argparse.ArgumentParser(description="Lead-time sensitivity test.")
    parser.add_argument("--extra-days", type=int, default=2,
                        help="days added to every lead time in the second run")
    parser.add_argument("--per-category", type=int, default=40,
                        help="random products per category (store CA_1 only)")
    return parser.parse_args()


def label_next_7_days(lost):
    """1 if there is lost demand on any of the next 7 days (NaN when unknown)."""
    stock_out = (lost > 0).astype(float)
    ahead = stock_out.shift(-1)                      # tomorrow
    return ahead[::-1].rolling(7, min_periods=1).max()[::-1]


def summarise(daily, periods, scenario):
    """Metrics per category and period, on days when the product is on sale."""
    daily = daily[daily["on_sale"] == 1].copy()
    daily["category"] = daily["item_id"].str.split("_").str[0]
    out = []
    for name in ("block_a", "block_b"):
        first, last = periods[name]
        part = daily[(daily["date"] >= pd.Timestamp(first)) & (daily["date"] <= pd.Timestamp(last))]
        for cat, g in part.groupby("category"):
            out.append({
                "scenario": scenario, "category": cat, "period": name,
                "pct_demand_lost": round(100 * g["lost_sales"].sum() / g["demand"].sum(), 2),
                "pct_stockout_days": round(100 * (g["lost_sales"] > 0).mean(), 2),
                "pct_label_positive": round(100 * g["label"].mean(), 1),
            })
    return pd.DataFrame(out)


def run_scenario(extra_days, sample, terms, launch_mu, item_rank, config, n_days):
    """Simulate the sampled products with every lead time longer by extra_days."""
    terms = {k: dict(v, quoted_lead_days=v["quoted_lead_days"] + extra_days) for k, v in terms.items()}
    frames = []
    by_dept = defaultdict(list)
    for item_id, dept, units, on_sale in sample:
        by_dept[dept].append((item_id, dept, list(units)[:n_days], list(on_sale)[:n_days]))
    store = config["scope"]["stores"][0]
    for dept, rows in by_dept.items():
        daily, _ = simulate_chunk(store, dept, rows, 0, item_rank, terms, launch_mu, config)
        frames.append(daily)
    daily = pd.concat(frames, ignore_index=True)
    daily["label"] = daily.groupby("item_id", group_keys=False)["lost_sales"].apply(label_next_7_days)
    return daily


def main():
    args = parse_args()
    config = load_config()
    periods = load_periods()
    start = pd.Timestamp(str(config["data"]["start_date"])).date()
    last_dev = last_development_day()
    assert_not_sealed(start, last_dev)                       # the seal: development days only
    n_days = (last_dev - start).days + 1

    con = duckdb.connect(config["warehouse"]["path"], read_only=True)
    launch_mu = {(r.store_id, r.dept_id): float(r.avg_units)
                 for r in con.execute(LAUNCH_SQL).df().itertuples()}
    terms = {r[0]: dict(zip(["cat_id", "pack_size", "moq_packs", "review_days", "z",
                             "quoted_lead_days", "late_rate", "partial_rate"], r[1:]))
             for r in con.execute(TERMS_SQL).fetchall()}
    item_rank = {item: i for i, item in enumerate(sorted(terms))}

    store = config["scope"]["stores"][0]
    rows = con.execute(SERIES_SQL, [store]).fetchall()
    con.close()

    rng = np.random.default_rng(config["project"]["seed"])
    sample = []
    for cat in sorted({t["cat_id"] for t in terms.values()}):
        pool = [r for r in rows if terms[r[0]]["cat_id"] == cat]
        pick = rng.choice(len(pool), size=min(args.per_category, len(pool)), replace=False)
        sample += [pool[i] for i in sorted(pick)]
    print(f"{len(sample)} products, store {store}, days {start} to {last_dev}")

    results = []
    for extra, label in ((0, "normal"), (args.extra_days, f"lead +{args.extra_days} days")):
        daily = run_scenario(extra, sample, terms, launch_mu, item_rank, config, n_days)
        results.append(summarise(daily, periods, label))
    table = pd.concat(results, ignore_index=True)
    pd.set_option("display.width", 140)
    print(table.sort_values(["category", "period", "scenario"]).to_string(index=False))


if __name__ == "__main__":
    main()