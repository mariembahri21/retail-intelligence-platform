"""Builds a tiny fake warehouse in a folder, so the daily loop can be tested
without touching the real data.

Two stores, three products (one per category), 70 days of Poisson demand,
and the simulator's real engine run on top of it.
"""
import sys
from datetime import date, timedelta
from pathlib import Path

import duckdb
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from simulation.run_simulation import simulate_chunk, write_parquet  # noqa: E402

START = date(2011, 1, 29)
SIM_DAYS = 70
CALENDAR_DAYS = SIM_DAYS + 28        # like M5: the calendar runs 28 days past the last sale
STORES = {"CA_1": "CA", "TX_1": "TX"}
ITEMS = {  # item_id: (department, category, supplier, pack, review, service_level, z, lead)
    "FOODS_1_001": ("FOODS_1", "FOODS", "SUP_FOODS_1", 6, 1, 0.95, 1.6449, 2),
    "HOUSEHOLD_1_001": ("HOUSEHOLD_1", "HOUSEHOLD", "SUP_HOUSEHOLD_1", 12, 3, 0.92, 1.4051, 4),
    "HOBBIES_1_001": ("HOBBIES_1", "HOBBIES", "SUP_HOBBIES_1", 4, 7, 0.90, 1.2816, 7),
}
SIM_CONFIG = {
    "project": {"seed": 42},
    "data": {"start_date": START.isoformat()},
    "simulation": {
        "partial_fill_range": [0.6, 0.9],
        "losses": {"shrink_rate": 0.0003, "record_error_rate": 0.003, "count_every_days": 28,
                   "expiry_rate": {"FOODS": 0.004, "HOUSEHOLD": 0.0, "HOBBIES": 0.0}},
    },
}


def build(root: Path) -> Path:
    """Create root/data/processed/retail.duckdb and root/data/processed/sim/... Returns the db path."""
    processed = root / "data" / "processed"
    processed.mkdir(parents=True, exist_ok=True)
    db_path = processed / "retail.duckdb"
    rng = np.random.default_rng(0)

    calendar = []
    for i in range(CALENDAR_DAYS):
        day = START + timedelta(days=i)
        calendar.append((f"d_{i + 1}", day, 11101 + i // 7, day.strftime("%A"),
                         (i % 7) + 1, day.month, day.year, "", "", "", "", 0, 0, 0))
    sales, prices = [], []
    series = {}
    for store, state in STORES.items():
        for item, (dept, cat, *_rest) in ITEMS.items():
            units = rng.poisson(3, SIM_DAYS).tolist()
            series[(store, item)] = units
            sales += [(item, dept, cat, store, state, f"d_{i + 1}", u) for i, u in enumerate(units)]
            prices += [(store, item, 11101 + w, 2.5) for w in range(CALENDAR_DAYS // 7 + 1)]

    con = duckdb.connect(str(db_path))
    con.execute("CREATE SCHEMA raw")
    con.execute("CREATE SCHEMA sim")
    con.execute("""CREATE TABLE raw.calendar (d VARCHAR, date DATE, wm_yr_wk INTEGER, weekday VARCHAR,
        wday INTEGER, month INTEGER, year INTEGER, event_name_1 VARCHAR, event_type_1 VARCHAR,
        event_name_2 VARCHAR, event_type_2 VARCHAR, snap_CA INTEGER, snap_TX INTEGER, snap_WI INTEGER)""")
    con.executemany("INSERT INTO raw.calendar VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", calendar)
    con.execute("""CREATE TABLE raw.sales (item_id VARCHAR, dept_id VARCHAR, cat_id VARCHAR,
        store_id VARCHAR, state_id VARCHAR, d VARCHAR, units INTEGER)""")
    con.executemany("INSERT INTO raw.sales VALUES (?,?,?,?,?,?,?)", sales)
    con.execute("CREATE TABLE raw.prices (store_id VARCHAR, item_id VARCHAR, wm_yr_wk INTEGER, sell_price DECIMAL(8,2))")
    con.executemany("INSERT INTO raw.prices VALUES (?,?,?,?)", prices)
    con.execute("""CREATE TABLE sim.supplier (supplier_id VARCHAR, category VARCHAR, quoted_lead_days INTEGER,
        late_rate DOUBLE, partial_rate DOUBLE)""")
    con.execute("""CREATE TABLE sim.item_supply (item_id VARCHAR, dept_id VARCHAR, cat_id VARCHAR,
        supplier_id VARCHAR, pack_size INTEGER, moq_packs INTEGER, review_days INTEGER,
        service_level DOUBLE, z DOUBLE)""")
    terms = {}
    for item, (dept, cat, sup, pack, review, level, z, lead) in ITEMS.items():
        con.execute("INSERT INTO sim.supplier VALUES (?,?,?,?,?)", [sup, cat, lead, 0.15, 0.05])
        con.execute("INSERT INTO sim.item_supply VALUES (?,?,?,?,?,?,?,?,?)",
                    [item, dept, cat, sup, pack, 2, review, level, z])
        terms[item] = {"cat_id": cat, "pack_size": pack, "moq_packs": 2, "review_days": review, "z": z,
                       "quoted_lead_days": lead, "late_rate": 0.15, "partial_rate": 0.05}
    con.close()

    item_rank = {item: i for i, item in enumerate(sorted(ITEMS))}
    for store_no, store in enumerate(STORES):
        for item, (dept, *_rest) in ITEMS.items():
            units = series[(store, item)]
            launch_mu = float(np.mean(units))
            daily, orders = simulate_chunk(store, dept, [(item, dept, units, [True] * SIM_DAYS)],
                                           store_no, item_rank, terms, {(store, dept): launch_mu}, SIM_CONFIG)
            write_parquet(daily, processed / "sim" / "daily" / f"store_id={store}" / f"{dept}.parquet")
            if len(orders):
                write_parquet(orders, processed / "sim" / "orders" / f"store_id={store}" / f"{dept}.parquet")
    return db_path