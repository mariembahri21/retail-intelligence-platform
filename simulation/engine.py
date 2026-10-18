"""Simulation engine for ONE product.

Day 6: perfect suppliers. Day 7: late and partial deliveries.
Expiry/shrink (step 3 of the daily cycle) comes on Day 8.
The daily cycle follows docs/retailer_design.md.
"""
import math
from collections import defaultdict
from statistics import mean, pstdev

import numpy as np
import pandas as pd


def round_up_to_pack(qty, pack_size):
    """Round a quantity up to a whole number of packs."""
    return math.ceil(qty / pack_size) * pack_size


def demand_stats(history, fallback_mu):
    """Mean and standard deviation of the last 28 recorded daily sales.

    With fewer than 7 days of history we do not trust the numbers yet,
    so we use a fallback guess.
    """
    recent = history[-28:]
    if len(recent) < 7:
        return fallback_mu, fallback_mu
    return mean(recent), pstdev(recent)


def units_on_order(arrivals):
    """Units the shop believes are on the road (what it ORDERED)."""
    return sum(o["ordered_qty"] for orders in arrivals.values() for o in orders)


def simulate_product(
    demand,
    lead_days,
    review_days,
    pack_size,
    moq_packs,
    z,
    late_rate=0.0,
    partial_rate=0.0,
    partial_fill_range=(0.6, 0.9),
    max_late_days=4,
    rng=None,
    return_orders=False,
):
    """Run the retailer day by day for one product.

    demand: list of daily units that customers wanted (the real M5 sales).
    late_rate / partial_rate: chance that an order is late / only partly delivered.
    rng: numpy random generator (use a seed so results can be repeated).
    Returns one row per day (and, if return_orders=True, a table of orders too).
    """
    if rng is None:
        rng = np.random.default_rng(0)

    fallback_mu = mean(demand[:28])
    stock = round_up_to_pack(14 * fallback_mu, pack_size)  # opening delivery
    arrivals = defaultdict(list)  # day number -> orders arriving that morning
    order_log = []
    history = []                  # units actually sold, day after day
    rows = []

    for day, wanted in enumerate(demand):
        # 1. Deliveries arrive
        arriving = arrivals.pop(day, [])
        received = sum(o["delivered_qty"] for o in arriving)
        stock += received

        # 2. Customers buy
        sold = min(wanted, stock)
        lost_sales = wanted - sold
        stock -= sold
        history.append(sold)

        # 3. End-of-day losses: added on Day 8

        # 5. Review and order (step 4, recording the stock, is the row below)
        ordered = 0
        if day % review_days == 0:
            mu, sigma = demand_stats(history, fallback_mu)
            L, R = lead_days, review_days
            s = max(mu * L + z * sigma * math.sqrt(L), pack_size)
            S = max(mu * (L + R) + z * sigma * math.sqrt(L + R), 2 * pack_size)

            position = stock + units_on_order(arrivals)
            if position <= s:
                qty = round_up_to_pack(max(S - position, 0), pack_size)
                qty = max(qty, moq_packs * pack_size)

                # What the supplier will do. The shop cannot know it in advance.
                # We always draw the same 4 random numbers, so results stay
                # stable when a rate changes.
                is_late = rng.random() < late_rate
                extra_days = int(rng.integers(1, max_late_days + 1))
                is_partial = rng.random() < partial_rate
                fill = rng.uniform(*partial_fill_range)

                late_days = extra_days if is_late else 0
                delivered = max(1, int(qty * fill)) if is_partial else qty

                order = {
                    "order_day": day,
                    "ordered_qty": qty,
                    "expected_day": day + lead_days,
                    "arrival_day": day + lead_days + late_days,
                    "late_days": late_days,
                    "delivered_qty": delivered,
                }
                arrivals[order["arrival_day"]].append(order)
                order_log.append(order)
                ordered = qty

        rows.append({
            "day": day,
            "demand": wanted,
            "received": received,
            "sold": sold,
            "lost_sales": lost_sales,
            "end_stock": stock,
            "ordered": ordered,
            "on_order": units_on_order(arrivals),
        })

    daily = pd.DataFrame(rows)
    if return_orders:
        return daily, pd.DataFrame(order_log)
    return daily