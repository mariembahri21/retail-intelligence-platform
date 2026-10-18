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
    """Today's shelf = yesterday's shelf + received - sold - expired - shrunk."""
    yesterday = sim.end_stock.shift(1)
    balance = yesterday + sim.received - sim.sold - sim.expired - sim.shrunk
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




# ---------- Day 8: losses and stock counts ----------

def run_losses(demand, **kwargs):
    return simulate_product(
        demand, rng=np.random.default_rng(1), loss_rng=np.random.default_rng(2),
        **TERMS, **kwargs
    )


def test_no_loss_rates_means_no_losses(sim):
    assert (sim.expired == 0).all()
    assert (sim.shrunk == 0).all()
    assert (sim.record_error == 0).all()
    assert (sim.system_stock == sim.end_stock).all()


def test_expiry_is_recorded_so_shelf_and_computer_agree(demand):
    result = run_losses(demand, expiry_rate=0.05)
    assert result.expired.sum() > 0
    assert (result.system_stock == result.end_stock).all()


def test_shrink_is_invisible_so_computer_is_never_below_the_shelf(demand):
    result = run_losses(demand, shrink_rate=0.05, count_every_days=None)
    assert result.shrunk.sum() > 0
    assert (result.system_stock >= result.end_stock).all()
    assert (result.system_stock > result.end_stock).any()


def test_record_errors_are_between_1_and_3_units(demand):
    result = run_losses(demand, record_error_rate=1.0, count_every_days=None)
    errors = result.record_error
    assert (errors != 0).all()
    assert (errors.abs() >= 1).all()
    assert (errors.abs() <= 3).all()


def test_full_count_fixes_the_computer(demand):
    result = run_losses(demand, shrink_rate=0.05, record_error_rate=0.2, count_every_days=7)
    count_days = result[result.day % 7 == 6]
    assert (count_days.system_stock == count_days.end_stock).all()


def test_empty_shelf_found_triggers_a_count(demand):
    result = run_losses(demand, shrink_rate=0.05, count_every_days=None)
    empty_with_lost_sales = result[(result.lost_sales > 0) & (result.end_stock == 0)]
    assert len(empty_with_lost_sales) > 0
    assert (empty_with_lost_sales.system_stock == 0).all()


def test_losses_increase_lost_sales(demand):
    def average_lost(**kwargs):
        runs = [
            simulate_product(
                demand, rng=np.random.default_rng(seed),
                loss_rng=np.random.default_rng(seed + 1000), **TERMS, **kwargs
            ).lost_sales.sum()
            for seed in range(10)
        ]
        return sum(runs) / len(runs)

    assert average_lost(expiry_rate=0.03, shrink_rate=0.03) > average_lost()


def test_losses_are_repeatable(demand):
    kwargs = dict(expiry_rate=0.02, shrink_rate=0.02, record_error_rate=0.05)
    assert run_losses(demand, **kwargs).equals(run_losses(demand, **kwargs))