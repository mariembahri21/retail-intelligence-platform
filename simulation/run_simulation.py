"""Run the retail simulation for every store x product and save the results.

Usage (from the project root):
    python simulation/run_simulation.py               # full run
    python simulation/run_simulation.py --limit 5     # quick test: 5 products per chunk
    python simulation/run_simulation.py --redo        # recompute chunks that already exist

The run is split into chunks (one per store and department). A finished chunk is a
Parquet file. If the run stops, start it again: finished chunks are skipped.
"""
import argparse
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from simulation.engine import simulate_product  # noqa: E402

SERIES_SQL = """
WITH base AS (
    SELECT s.item_id, s.dept_id, CAST(SUBSTR(s.d, 3) AS INTEGER) AS day_no, s.units,
           (p.sell_price IS NOT NULL) AS on_sale
    FROM raw.sales s
    JOIN raw.calendar c USING (d)
    LEFT JOIN raw.prices p ON p.wm_yr_wk = c.wm_yr_wk
                          AND p.store_id = s.store_id AND p.item_id = s.item_id
    WHERE s.store_id = ?
)
SELECT item_id,
       ANY_VALUE(dept_id) AS dept_id,
       LIST(units ORDER BY day_no)   AS units,
       LIST(on_sale ORDER BY day_no) AS on_sale
FROM base
GROUP BY item_id
ORDER BY item_id
"""

LAUNCH_SQL = """
SELECT s.store_id, s.dept_id, AVG(s.units) AS avg_units
FROM raw.sales s
JOIN raw.calendar c USING (d)
JOIN raw.prices p ON p.wm_yr_wk = c.wm_yr_wk
                 AND p.store_id = s.store_id AND p.item_id = s.item_id
GROUP BY s.store_id, s.dept_id
"""

TERMS_SQL = """
SELECT i.item_id, i.cat_id, i.pack_size, i.moq_packs, i.review_days, i.z,
       s.quoted_lead_days, s.late_rate, s.partial_rate
FROM sim.item_supply i
JOIN sim.supplier s USING (supplier_id)
ORDER BY i.item_id
"""


def load_config():
    with open("config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def parse_args():
    parser = argparse.ArgumentParser(description="Run the retail simulation.")
    parser.add_argument("--limit", type=int, default=None,
                        help="only simulate the first N products of each chunk (test run)")
    parser.add_argument("--redo", action="store_true",
                        help="recompute chunks even if their file already exists")
    return parser.parse_args()


def write_parquet(frame, path):
    """Write a DataFrame as a Parquet file. The file appears only when complete."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    mem = duckdb.connect()
    mem.register("frame", frame)
    mem.execute(f"COPY frame TO '{tmp.as_posix()}' (FORMAT PARQUET)")
    mem.close()
    os.replace(tmp, path)


def simulate_chunk(store, dept, rows, store_no, item_rank, terms, launch_mu, config):
    """Simulate every product of one store and department."""
    sim_cfg = config["simulation"]
    losses = sim_cfg["losses"]
    seed = config["project"]["seed"]
    daily_frames, order_frames = [], []

    for item_id, _dept, units, on_sale in rows:
        t = terms[item_id]
        series_no = store_no * 100_000 + item_rank[item_id]   # stable id -> repeatable random numbers
        daily, orders = simulate_product(
            units,
            lead_days=t["quoted_lead_days"],
            review_days=t["review_days"],
            pack_size=t["pack_size"],
            moq_packs=t["moq_packs"],
            z=t["z"],
            on_sale=on_sale,
            launch_mu=launch_mu[(store, dept)],
            late_rate=t["late_rate"],
            partial_rate=t["partial_rate"],
            partial_fill_range=tuple(sim_cfg["partial_fill_range"]),
            expiry_rate=losses["expiry_rate"][t["cat_id"]],
            shrink_rate=losses["shrink_rate"],
            record_error_rate=losses["record_error_rate"],
            count_every_days=losses["count_every_days"],
            rng=np.random.default_rng([seed, 1, series_no]),
            loss_rng=np.random.default_rng([seed, 2, series_no]),
            return_orders=True,
        )
        daily.insert(0, "item_id", item_id)
        daily_frames.append(daily)
        if len(orders):
            orders.insert(0, "item_id", item_id)
            order_frames.append(orders)

    daily = pd.concat(daily_frames, ignore_index=True)
    daily.insert(0, "store_id", store)
    start = pd.Timestamp(str(config["data"]["start_date"]))
    daily.insert(2, "date", start + pd.to_timedelta(daily["day"], unit="D"))
    for col in daily.columns:
        if daily[col].dtype == "int64":
            daily[col] = daily[col].astype("int32")

    if order_frames:
        orders = pd.concat(order_frames, ignore_index=True)
        orders.insert(0, "store_id", store)
        for col in orders.columns:
            if orders[col].dtype == "int64":
                orders[col] = orders[col].astype("int32")
    else:
        orders = pd.DataFrame()
    return daily, orders


def main():
    args = parse_args()
    config = load_config()
    out_root = Path("data/processed") / ("sim_test" if args.limit else "sim")

    con = duckdb.connect(config["warehouse"]["path"], read_only=True)
    launch_df = con.execute(LAUNCH_SQL).df()
    launch_mu = {(r.store_id, r.dept_id): float(r.avg_units) for r in launch_df.itertuples()}
    terms = {r[0]: dict(zip(
        ["cat_id", "pack_size", "moq_packs", "review_days", "z",
         "quoted_lead_days", "late_rate", "partial_rate"], r[1:]))
        for r in con.execute(TERMS_SQL).fetchall()}
    item_rank = {item: i for i, item in enumerate(sorted(terms))}

    started = time.time()
    total_series = total_rows = 0
    for store_no, store in enumerate(config["scope"]["stores"]):
        by_dept = defaultdict(list)
        for row in con.execute(SERIES_SQL, [store]).fetchall():
            by_dept[row[1]].append(row)

        for dept in sorted(by_dept):
            rows = by_dept[dept][: args.limit]
            daily_path = out_root / "daily" / f"store_id={store}" / f"{dept}.parquet"
            orders_path = out_root / "orders" / f"store_id={store}" / f"{dept}.parquet"
            if daily_path.exists() and not args.redo:
                print(f"{store} {dept}: already done, skipped")
                continue

            t0 = time.time()
            daily, orders = simulate_chunk(store, dept, rows, store_no, item_rank,
                                           terms, launch_mu, config)
            if len(orders):
                write_parquet(orders, orders_path)
            write_parquet(daily, daily_path)          # written last = the chunk is complete
            total_series += len(rows)
            total_rows += len(daily)
            print(f"{store} {dept}: {len(rows)} products, {len(daily):,} rows, "
                  f"{(time.time() - t0) / 60:.1f} min")

    con.close()
    print(f"Done: {total_series} products, {total_rows:,} rows, "
          f"{(time.time() - started) / 60:.1f} min. Output: {out_root}")


if __name__ == "__main__":
    main()