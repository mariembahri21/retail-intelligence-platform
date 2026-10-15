"""Generate the simulation master data: suppliers and item-supply terms.

Run from the project root:  python simulation/master_data.py
Creates the tables sim.supplier and sim.item_supply in the DuckDB warehouse.
The same seed in config.yaml always produces exactly the same tables.
"""
from pathlib import Path
from statistics import NormalDist

import duckdb
import numpy as np
import pandas as pd
import yaml

CONFIG_PATH = Path("config.yaml")


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def build_suppliers(config: dict, rng: np.random.Generator) -> pd.DataFrame:
    """One row per supplier, with its own late-delivery and partial-delivery rates."""
    sim = config["simulation"]
    rows = []
    for category, params in sim["categories"].items():
        for i in range(1, params["n_suppliers"] + 1):
            rows.append(
                {
                    "supplier_id": f"SUP_{category}_{i}",
                    "category": category,
                    "quoted_lead_days": params["quoted_lead_days"],
                    "late_rate": round(rng.uniform(*params["late_rate_range"]), 3),
                    "partial_rate": round(rng.uniform(*sim["partial_rate_range"]), 3),
                }
            )
    return pd.DataFrame(rows)


def build_item_supply(
    items: pd.DataFrame, suppliers: pd.DataFrame, config: dict, rng: np.random.Generator
) -> pd.DataFrame:
    """One row per product: its supplier and its ordering terms."""
    sim = config["simulation"]
    unknown = set(items["cat_id"]) - set(sim["categories"])
    if unknown:
        raise ValueError(f"Categories missing from config.yaml: {sorted(unknown)}")

    parts = []
    for category, params in sim["categories"].items():
        part = items[items["cat_id"] == category].copy()
        supplier_ids = suppliers.loc[suppliers["category"] == category, "supplier_id"].to_numpy()
        part["supplier_id"] = rng.choice(supplier_ids, size=len(part))
        part["pack_size"] = params["pack_size"]
        part["moq_packs"] = sim["moq_packs"]
        part["review_days"] = params["review_days"]
        part["service_level"] = params["service_level"]
        part["z"] = round(NormalDist().inv_cdf(params["service_level"]), 4)
        parts.append(part)
    return pd.concat(parts, ignore_index=True).sort_values("item_id").reset_index(drop=True)


def main() -> None:
    config = load_config()
    db_path = Path(config["warehouse"]["path"])
    rng = np.random.default_rng(config["project"]["seed"])

    con = duckdb.connect(str(db_path))
    con.execute("CREATE SCHEMA IF NOT EXISTS sim")

    items = con.execute(
        "SELECT DISTINCT item_id, dept_id, cat_id FROM raw.sales ORDER BY item_id"
    ).df()

    suppliers = build_suppliers(config, rng)
    item_supply = build_item_supply(items, suppliers, config, rng)

    con.register("suppliers_df", suppliers)
    con.execute("""
        CREATE OR REPLACE TABLE sim.supplier AS
        SELECT
            supplier_id::VARCHAR      AS supplier_id,
            category::VARCHAR         AS category,
            quoted_lead_days::INTEGER AS quoted_lead_days,
            late_rate::DOUBLE         AS late_rate,
            partial_rate::DOUBLE      AS partial_rate
        FROM suppliers_df
    """)

    con.register("item_supply_df", item_supply)
    con.execute("""
        CREATE OR REPLACE TABLE sim.item_supply AS
        SELECT
            item_id::VARCHAR       AS item_id,
            dept_id::VARCHAR       AS dept_id,
            cat_id::VARCHAR        AS cat_id,
            supplier_id::VARCHAR   AS supplier_id,
            pack_size::INTEGER     AS pack_size,
            moq_packs::INTEGER     AS moq_packs,
            review_days::INTEGER   AS review_days,
            service_level::DOUBLE  AS service_level,
            z::DOUBLE              AS z
        FROM item_supply_df
    """)

    for name in ("sim.supplier", "sim.item_supply"):
        rows = con.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
        print(f"{name}: {rows:,} rows")
    con.close()


if __name__ == "__main__":
    main()