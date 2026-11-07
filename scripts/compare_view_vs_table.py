"""Time the same query on fct_inventory_daily as a TABLE (what dbt built)
and as a VIEW (the same SQL, recomputed at every query).

Usage (from the project root, with no notebook or dbt connected to the database):
    python scripts/compare_view_vs_table.py
"""
import statistics
import time
from pathlib import Path

import duckdb
import yaml

ROOT = Path(__file__).resolve().parent.parent
RUNS = 3

with open(ROOT / "config.yaml", encoding="utf-8") as f:
    config = yaml.safe_load(f)

con = duckdb.connect((ROOT / config["warehouse"]["path"]).as_posix(), read_only=True)

# The same logic as stg_sim_daily + fct_inventory_daily, but as a view over the
# Parquet files (temporary, nothing is written). A view recomputes everything
# at every query. We give the absolute path, so it works from any folder.
parquet = (ROOT / "data" / "processed" / "sim" / "daily" / "*" / "*.parquet").as_posix()
con.execute(f"""
    CREATE TEMP VIEW inventory_as_view AS
    SELECT
        store_id, item_id, cast(date AS date) AS date,
        on_sale AS is_on_sale, opening AS opening_units, received AS received_units,
        demand AS demand_units, sold AS sold_units, lost_sales AS lost_sales_units,
        expired AS expired_units, shrunk AS shrunk_units, cleared AS cleared_units,
        record_error AS record_error_units, count_adjustment AS count_adjustment_units,
        end_stock AS end_stock_units, system_stock AS system_stock_units,
        ordered AS ordered_units, on_order AS on_order_units,
        lost_sales > 0 AS is_stockout,
        system_stock - end_stock AS stock_gap_units
    FROM read_parquet('{parquet}', hive_partitioning = false)
""")

QUERY = """
    SELECT p.cat_id, year(i.date) AS year,
           round(100.0 * avg(i.is_stockout::int), 2) AS pct_stockout_days,
           sum(i.lost_sales_units) AS lost_units
    FROM {source} AS i
    JOIN main.dim_product AS p USING (item_id)
    WHERE i.is_on_sale
    GROUP BY 1, 2
    ORDER BY 1, 2
"""

sources = {
    "table (dbt built)": "main.fct_inventory_daily",
    "view (same SQL)": "inventory_as_view",
}
results, timings = {}, {name: [] for name in sources}

for name, source in sources.items():          # one warm-up run each, not timed
    con.execute(QUERY.format(source=source)).fetchall()

for _ in range(RUNS):                          # then alternate, so neither is favoured
    for name, source in sources.items():
        start = time.perf_counter()
        results[name] = con.execute(QUERY.format(source=source)).fetchall()
        timings[name].append(time.perf_counter() - start)

print(f"Same query, {RUNS} timed runs each (seconds)")
for name, values in timings.items():
    print(f"  {name:20s} best {min(values):6.2f}   average {statistics.mean(values):6.2f}")

same = results["table (dbt built)"] == results["view (same SQL)"]
print("Same answer from both:", same)
rows = con.execute("SELECT count(*) FROM main.fct_inventory_daily").fetchone()[0]
print(f"Rows in the table: {rows:,}")
con.close()