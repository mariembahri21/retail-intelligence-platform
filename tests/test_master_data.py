"""Checks on the simulated master data (sim.supplier and sim.item_supply).

Run from the project root:  pytest tests/test_master_data.py -v
"""
from statistics import NormalDist

import duckdb
import pytest
import yaml


@pytest.fixture(scope="module")
def config():
    with open("config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def con(config):
    connection = duckdb.connect(config["warehouse"]["path"], read_only=True)
    yield connection
    connection.close()


CATEGORIES = ["FOODS", "HOUSEHOLD", "HOBBIES"]


# ---------- sim.supplier ----------

def test_supplier_count_matches_config(con, config):
    expected = sum(c["n_suppliers"] for c in config["simulation"]["categories"].values())
    n = con.execute("SELECT COUNT(*) FROM sim.supplier").fetchone()[0]
    assert n == expected


def test_supplier_ids_unique(con):
    n, n_distinct = con.execute(
        "SELECT COUNT(*), COUNT(DISTINCT supplier_id) FROM sim.supplier"
    ).fetchone()
    assert n == n_distinct


@pytest.mark.parametrize("category", CATEGORIES)
def test_suppliers_per_category(con, config, category):
    rules = config["simulation"]["categories"][category]
    n = con.execute(
        "SELECT COUNT(*) FROM sim.supplier WHERE category = ?", [category]
    ).fetchone()[0]
    assert n == rules["n_suppliers"]


@pytest.mark.parametrize("category", CATEGORIES)
def test_supplier_rates_inside_config_ranges(con, config, category):
    sim = config["simulation"]
    rules = sim["categories"][category]
    late_lo, late_hi = rules["late_rate_range"]
    part_lo, part_hi = sim["partial_rate_range"]
    bad = con.execute(
        """
        SELECT COUNT(*) FROM sim.supplier
        WHERE category = ?
          AND (late_rate NOT BETWEEN ? AND ?
               OR partial_rate NOT BETWEEN ? AND ?
               OR quoted_lead_days <> ?)
        """,
        [category, late_lo, late_hi, part_lo, part_hi, rules["quoted_lead_days"]],
    ).fetchone()[0]
    assert bad == 0


# ---------- sim.item_supply ----------

def test_one_row_per_item(con):
    n, n_distinct = con.execute(
        "SELECT COUNT(*), COUNT(DISTINCT item_id) FROM sim.item_supply"
    ).fetchone()
    assert n == n_distinct


def test_same_items_as_sales(con):
    only_in_sales = con.execute(
        """
        SELECT COUNT(*) FROM (SELECT DISTINCT item_id FROM raw.sales) s
        LEFT JOIN sim.item_supply i USING (item_id)
        WHERE i.item_id IS NULL
        """
    ).fetchone()[0]
    only_in_supply = con.execute(
        """
        SELECT COUNT(*) FROM sim.item_supply i
        LEFT JOIN (SELECT DISTINCT item_id FROM raw.sales) s USING (item_id)
        WHERE s.item_id IS NULL
        """
    ).fetchone()[0]
    assert only_in_sales == 0
    assert only_in_supply == 0


def test_every_supplier_exists(con):
    orphans = con.execute(
        """
        SELECT COUNT(*) FROM sim.item_supply i
        LEFT JOIN sim.supplier s USING (supplier_id)
        WHERE s.supplier_id IS NULL
        """
    ).fetchone()[0]
    assert orphans == 0


def test_supplier_belongs_to_item_category(con):
    wrong = con.execute(
        """
        SELECT COUNT(*) FROM sim.item_supply i
        JOIN sim.supplier s USING (supplier_id)
        WHERE i.cat_id <> s.category
        """
    ).fetchone()[0]
    assert wrong == 0


def test_no_nulls(con):
    nulls = con.execute(
        """
        SELECT COUNT(*) FROM sim.item_supply
        WHERE item_id IS NULL OR supplier_id IS NULL OR pack_size IS NULL
           OR moq_packs IS NULL OR review_days IS NULL
           OR service_level IS NULL OR z IS NULL
        """
    ).fetchone()[0]
    assert nulls == 0


@pytest.mark.parametrize("category", CATEGORIES)
def test_ordering_terms_match_config(con, config, category):
    sim = config["simulation"]
    rules = sim["categories"][category]
    rows = con.execute(
        """
        SELECT DISTINCT pack_size, moq_packs, review_days, service_level
        FROM sim.item_supply WHERE cat_id = ?
        """,
        [category],
    ).fetchall()
    assert rows == [
        (rules["pack_size"], sim["moq_packs"], rules["review_days"], rules["service_level"])
    ]


@pytest.mark.parametrize("category", CATEGORIES)
def test_z_matches_service_level(con, config, category):
    level = config["simulation"]["categories"][category]["service_level"]
    expected = NormalDist().inv_cdf(level)
    zs = [r[0] for r in con.execute(
        "SELECT DISTINCT z FROM sim.item_supply WHERE cat_id = ?", [category]
    ).fetchall()]
    assert len(zs) == 1
    assert abs(zs[0] - expected) < 1e-3