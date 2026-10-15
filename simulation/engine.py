"""First version of the simulation engine: ONE product.

No late deliveries, no partial deliveries, no expiry/shrink yet (Days 7-8).
The daily cycle follows docs/retailer_design.md.
"""
import math
from collections import defaultdict
from statistics import mean, pstdev

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


def simulate_product(demand, lead_days, review_days, pack_size, moq_packs, z):
    """Run the retailer day by day for one product.

    demand: list of daily units that customers wanted (the real M5 sales).
    Returns one row per day.
    """
    fallback_mu = mean(demand[:28])
    stock = round_up_to_pack(14 * fallback_mu, pack_size)  # opening delivery
    arrivals = defaultdict(int)  # day number -> units arriving that morning
    history = []                 # units actually sold, day after day
    rows = []

    for day, wanted in enumerate(demand):
        # 1. Deliveries arrive
        received = arrivals.pop(day, 0)
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

            on_order = sum(arrivals.values())
            position = stock + on_order
            if position <= s:
                qty = round_up_to_pack(max(S - position, 0), pack_size)
                qty = max(qty, moq_packs * pack_size)
                arrivals[day + lead_days] += qty
                ordered = qty

        rows.append({
            "day": day,
            "demand": wanted,
            "received": received,
            "sold": sold,
            "lost_sales": lost_sales,
            "end_stock": stock,
            "ordered": ordered,
            "on_order": sum(arrivals.values()),
        })

    return pd.DataFrame(rows)