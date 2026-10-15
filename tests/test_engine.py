"""Checks on the simulation engine, using made-up demand (no database needed).

Run from the project root:  pytest tests/test_engine.py -v
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pytest

from simulation.engine import simulate_product

# FOODS-like ordering terms
TERMS = dict(lead_days=2, review_days=1, pack_size=6, moq_packs=2, z=1.6449)


@pytest.fixture(scope="module")
def demand():
    """500 days of jumpy, intermittent demand (about 40% zero days)."""
    rng = np.random.default_rng(0)
    values = rng.poisson(6, 500)
    values[rng.random(500) < 0.4] = 0
    return [int(v) for v in values]


@pytest.fixture(scope="module")
def sim(demand):
    return simulate_product(demand, **TERMS)


def test_one_row_per_day(sim, demand):
    assert len(sim) == len(demand)


def test_stock_never_negative(sim):
    assert (sim.end_stock >= 0).all()


def test_sold_plus_lost_equals_demand(sim):
    assert (sim.sold + sim.lost_sales == sim.demand).all()


def test_cannot_sell_more_than_demand_or_stock(sim):
    assert (sim.sold <= sim.demand).all()
    assert (sim.lost_sales >= 0).all()


def test_stock_balance(sim):
    """Today's stock = yesterday's stock + received - sold."""
    yesterday = sim.end_stock.shift(1)
    balance = yesterday + sim.received - sim.sold
    assert (balance.iloc[1:] == sim.end_stock.iloc[1:]).all()


def test_orders_are_whole_packs_and_respect_moq(sim):
    orders = sim.ordered[sim.ordered > 0]
    assert len(orders) > 0
    assert (orders % TERMS["pack_size"] == 0).all()
    assert (orders >= TERMS["moq_packs"] * TERMS["pack_size"]).all()


def test_orders_arrive_after_lead_time(sim):
    """Each order placed on day t arrives on day t + lead_days, no earlier or later."""
    lead = TERMS["lead_days"]
    expected = sim.ordered.shift(lead).fillna(0)
    assert (sim.received.iloc[lead:] == expected.iloc[lead:]).all()


def test_no_demand_means_no_sales_and_no_lost_sales():
    result = simulate_product([0] * 60, **TERMS)
    assert result.sold.sum() == 0
    assert result.lost_sales.sum() == 0


def test_tiny_stock_and_big_demand_creates_lost_sales():
    """A sudden spike bigger than the stock must show up as lost sales."""
    demand = [1] * 40 + [500] + [1] * 20
    result = simulate_product(demand, **TERMS)
    assert result.lost_sales.sum() > 0


def test_same_input_same_output(demand):
    first = simulate_product(demand, **TERMS)
    second = simulate_product(demand, **TERMS)
    assert first.equals(second)