"""Simulation engine for ONE product.

Day 6: perfect suppliers. Day 7: late and partial deliveries.
Day 8: losses (expiry, shrink, wrong records) and stock counts.
The daily cycle follows docs/retailer_design.md.

Two stock numbers exist:
  physical = units really on the shelf (customers buy from this)
  system   = what the shop's computer believes (the ordering policy uses this)
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
    expiry_rate=0.0,
    shrink_rate=0.0,
    record_error_rate=0.0,
    count_every_days=28,
    rng=None,
    loss_rng=None,
    return_orders=False,
):
    """Run the retailer day by day for one product.

    demand: list of daily units that customers wanted (the real M5 sales).
    late_rate / partial_rate: chance that an order is late / only partly delivered.
    expiry_rate / shrink_rate: share of the shelf lost per day (expired / stolen or damaged).
    record_error_rate: daily chance that the computer's number is wrong by 1 to 3 units.
    count_every_days: a full stock count fixes the computer's number this often.
    rng: random generator for the suppliers; loss_rng: a separate one for the losses
    (separate, so adding losses does not change the supplier results).
    Returns one row per day (and, if return_orders=True, a table of orders too).
    """
    if rng is None:
        rng = np.random.default_rng(0)
    if loss_rng is None:
        loss_rng = np.random.default_rng(1)

    fallback_mu = mean(demand[:28])
    physical = round_up_to_pack(14 * fallback_mu, pack_size)  # opening delivery
    system = physical
    arrivals = defaultdict(list)  # day number -> orders arriving that morning
    order_log = []
    history = []                  # units actually sold, day after day
    rows = []

    for day, wanted in enumerate(demand):
        # 1. Deliveries arrive (shelf and computer both get them)
        arriving = arrivals.pop(day, [])
        received = sum(o["delivered_qty"] for o in arriving)
        physical += received
        system += received

        # 2. Customers buy (from the real shelf)
        sold = min(wanted, physical)
        lost_sales = wanted - sold
        physical -= sold
        system = max(system - sold, 0)
        history.append(sold)

        # 3. End-of-day losses
        expired = int(loss_rng.binomial(physical, expiry_rate))
        physical -= expired
        system = max(system - expired, 0)      # thrown away AND recorded

        shrunk = int(loss_rng.binomial(physical, shrink_rate))
        physical -= shrunk                     # theft/damage: nobody notices yet

        record_error = 0
        if loss_rng.random() < record_error_rate:
            record_error = int(loss_rng.choice([-3, -2, -1, 1, 2, 3]))
            system = max(system + record_error, 0)   # the computer is now wrong

        # A count fixes the computer's number. It happens when a customer finds an
        # empty shelf while the computer says there is stock, and at regular full counts.
        count_adjustment = 0
        empty_shelf_found = lost_sales > 0 and physical == 0 and system > 0
        full_count_day = bool(count_every_days) and day % count_every_days == count_every_days - 1
        if empty_shelf_found or full_count_day:
            count_adjustment = physical - system
            system = physical

        # 5. Review and order (step 4, recording the stock, is the row below)
        ordered = 0
        if day % review_days == 0:
            mu, sigma = demand_stats(history, fallback_mu)
            L, R = lead_days, review_days
            s = max(mu * L + z * sigma * math.sqrt(L), pack_size)
            S = max(mu * (L + R) + z * sigma * math.sqrt(L + R), 2 * pack_size)

            position = system + units_on_order(arrivals)   # the policy sees the computer's number
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
            "expired": expired,
            "shrunk": shrunk,
            "record_error": record_error,
            "count_adjustment": count_adjustment,
            "end_stock": physical,
            "system_stock": system,
            "ordered": ordered,
            "on_order": units_on_order(arrivals),
        })

    daily = pd.DataFrame(rows)
    if return_orders:
        return daily, pd.DataFrame(order_log)
    return daily