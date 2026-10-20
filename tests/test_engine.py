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
    """Today's shelf = yesterday's shelf + opening + received - sold - expired - shrunk - cleared."""
    yesterday = sim.end_stock.shift(1)
    balance = (yesterday + sim.opening + sim.received
               - sim.sold - sim.expired - sim.shrunk - sim.cleared)
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



# ---------- Day 7: late and partial deliveries ----------

def test_late_orders_arrive_1_to_4_days_late(demand):
    _, orders = simulate_product(
        demand, late_rate=1.0, rng=np.random.default_rng(1), return_orders=True, **TERMS
    )
    extra = orders.arrival_day - orders.expected_day
    assert (extra >= 1).all()
    assert (extra <= 4).all()


def test_partial_orders_bring_60_to_90_percent(demand):
    _, orders = simulate_product(
        demand, partial_rate=1.0, rng=np.random.default_rng(1), return_orders=True, **TERMS
    )
    assert (orders.delivered_qty < orders.ordered_qty).all()
    assert (orders.delivered_qty >= (0.6 * orders.ordered_qty).astype(int)).all()
    assert (orders.delivered_qty <= 0.9 * orders.ordered_qty).all()


def test_received_equals_delivered_orders(demand):
    daily, orders = simulate_product(
        demand, late_rate=0.3, partial_rate=0.3,
        rng=np.random.default_rng(2), return_orders=True, **TERMS
    )
    arrived = orders[orders.arrival_day < len(demand)]
    assert daily.received.sum() == arrived.delivered_qty.sum()
    assert daily.received.sum() <= orders.ordered_qty.sum()


def test_observed_rates_are_close_to_the_inputs():
    rng = np.random.default_rng(3)
    long_demand = [int(v) for v in rng.poisson(6, 3000)]
    _, orders = simulate_product(
        long_demand, late_rate=0.2, partial_rate=0.1,
        rng=np.random.default_rng(4), return_orders=True, **TERMS
    )
    late_share = (orders.late_days > 0).mean()
    partial_share = (orders.delivered_qty < orders.ordered_qty).mean()
    assert abs(late_share - 0.2) < 0.06
    assert abs(partial_share - 0.1) < 0.05


def test_same_seed_same_result_different_seed_different_result(demand):
    kwargs = dict(late_rate=0.3, partial_rate=0.3, **TERMS)
    a = simulate_product(demand, rng=np.random.default_rng(7), **kwargs)
    b = simulate_product(demand, rng=np.random.default_rng(7), **kwargs)
    c = simulate_product(demand, rng=np.random.default_rng(8), **kwargs)
    assert a.equals(b)
    assert not a.equals(c)


def test_bad_suppliers_lose_more_sales_than_perfect_ones(demand):
    perfect = simulate_product(demand, **TERMS).lost_sales.sum()
    bad = [
        simulate_product(
            demand, late_rate=0.3, partial_rate=0.3,
            rng=np.random.default_rng(seed), **TERMS
        ).lost_sales.sum()
        for seed in range(10)
    ]
    assert sum(bad) / len(bad) > perfect



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





# ---------- Day 9: products that are not on sale ----------

def test_default_is_always_on_sale(demand):
    a = simulate_product(demand, **TERMS)
    b = simulate_product(demand, on_sale=[True] * len(demand), **TERMS)
    assert a.equals(b)


def test_nothing_happens_before_launch():
    demand = [0] * 60 + [5] * 100
    on_sale = [False] * 60 + [True] * 100
    result = simulate_product(demand, on_sale=on_sale, launch_mu=5, **TERMS)
    before = result[result.day < 60]
    assert (before.end_stock == 0).all()
    assert (before.system_stock == 0).all()
    assert (before.ordered == 0).all()
    assert (before.received == 0).all()
    assert (before.opening == 0).all()


def test_opening_delivery_on_launch_day():
    demand = [0] * 60 + [5] * 100
    on_sale = [False] * 60 + [True] * 100
    result = simulate_product(demand, on_sale=on_sale, launch_mu=5, **TERMS)
    launch = result.iloc[60]
    assert launch.opening == 72                      # 14 days x 5 units, in packs of 6
    assert launch.end_stock == 72 - launch.sold
    assert (result.opening > 0).sum() == 1


def test_leaving_the_shelf_clears_stock_and_cancels_orders():
    demand = [6] * 100 + [0] * 50 + [6] * 100
    on_sale = [True] * 100 + [False] * 50 + [True] * 100
    daily, orders = simulate_product(
        demand, on_sale=on_sale, launch_mu=6, return_orders=True, **TERMS
    )
    gap = daily[(daily.day >= 100) & (daily.day < 150)]
    assert daily.cleared.iloc[100] == daily.end_stock.iloc[99]
    assert (gap.end_stock == 0).all()
    assert (gap.system_stock == 0).all()
    assert (gap.ordered == 0).all()
    assert (gap.received == 0).all()
    assert daily.opening.iloc[150] > 0               # a new first delivery on return
    assert orders.cancelled.any()                    # orders on the road were cancelled


def test_stock_balance_with_gaps(demand):
    on_sale = [(day // 40) % 2 == 0 for day in range(len(demand))]
    result = simulate_product(
        demand, on_sale=on_sale, launch_mu=5, expiry_rate=0.02, shrink_rate=0.02, **TERMS
    )
    yesterday = result.end_stock.shift(1)
    balance = (yesterday + result.opening + result.received
               - result.sold - result.expired - result.shrunk - result.cleared)
    assert (balance.iloc[1:] == result.end_stock.iloc[1:]).all()
    assert (result.end_stock[~result.on_sale] == 0).all()