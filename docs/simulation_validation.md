# Simulation validation

This page records how I checked that the simulated retailer behaves in a believable
way, what I decided as a result, and what the simulator cannot do.

## 1. What was run

| Item | Value |
|---|---|
| Stores | CA_1, TX_1, WI_1 |
| Products | 9,147 store-product series (3,049 per store) |
| Days | 1,941 (2011-01-29 to 2016-05-22) |
| Output | 17,754,327 daily rows in 21 chunks (store x department) |
| Run time | 6.0 minutes |
| Seed | 42 (each product has its own random generator, so a rerun gives the same result) |

Demand is the real M5 sales. Stock, deliveries, losses and orders are simulated.
The design is in `retailer_design.md`.

## 2. Automatic checks

| Test file | What it protects |
|---|---|
| `tests/test_raw_data.py` (16) | The raw M5 data loaded correctly. |
| `tests/test_master_data.py` (about 18) | Suppliers and ordering terms match the config. |
| `tests/test_engine.py` (29) | The rules of one product: stock never negative, balance equation, pack size and minimum order, late (1-4 days) and partial (60-90%) deliveries, losses, stock counts, products not on sale. |
| `tests/test_simulation_output.py` (10) | The full output: one row per product per day, no duplicates, demand equals the real M5 sales, `sold + lost = demand`, the daily stock balance, orders match the daily totals. |
| `tests/test_periods.py` (9) | The calendar: periods follow each other with no hole, burn-in is 28 days, gaps are 7 days, the live test is refused by the seal. |

## 3. Results by period (development days only)

Share of demand lost, on days when the product is on sale:

| Category | Burn-in | Block A | Block B |
|---|---|---|---|
| FOODS | 14.5% | 5.2% | 4.8% |
| HOUSEHOLD | 8.6% | 5.7% | 5.2% |
| HOBBIES | 41.0% | 15.9% | 14.6% |

Share of days with a stockout, in Block A: FOODS 1.8%, HOUSEHOLD 0.9%, HOBBIES 3.7%.
Block A and Block B are close in every category, so the simulator is stable over time.

### The 7-day stockout label

The label is 1 if there is lost demand on any of the next 7 days.

| Category | Block A | Block B |
|---|---|---|
| FOODS | 8.2% | 7.1% |
| HOBBIES | 12.4% | 12.0% |
| HOUSEHOLD | 3.5% | 3.4% |

About 7% of rows are positive (1 in 14). The rate is lower than 7 times the stockout-day
rate because stockouts come in runs, most strongly for HOBBIES (7-day delivery).

## 4. Findings and decisions

1. **HOBBIES is the hard category.** It loses about 15% of demand against about 5%
   for FOODS and HOUSEHOLD. Causes: weekly review plus a 7-day delivery (a 14-day
   blind period), 15-25% late deliveries and the lowest service level (90%). A longer
   demand window did not help (28/56/91 days gave 14.3/14.7/14.5% lost).
   *Decision:* keep it. The baseline keeps realistic differences between categories.
   Faster review and a higher service level will be tested later as separate scenarios.
2. **Launch stockouts come from big sellers.** In the first 14 days, the biggest-selling
   third of products loses 27% (FOODS), 61% (HOBBIES) and 13% (HOUSEHOLD); small and
   medium sellers lose under 2%. Cause: opening stock and first orders are sized from the
   department average until a product has 7 days of history.
   *Decision:* keep it (a real launch without history has the same problem). The burn-in
   is never used by a model.
3. **Calibration target.** The first target (stockouts on 3-10% of days) was written
   before the simulator existed. The target is now the label's positive rate, which is
   3-12%. *Decision:* no recalibration.
4. **Sensitivity to lead times.** With every lead time 2 days longer (sample of 120
   products, store CA_1), lost demand rises by 0.3 to 2.8 points and the label by about 1
   to 3 points. The direction is the expected one, and the ranking of the categories does
   not change. The findings are robust to this choice.

## 5. The live test is sealed

The live test (2015-07-01 to 2016-04-30) and the live replay (2016-05-01 to 2016-05-22)
are generated but not used for any decision. `simulation/periods.py` provides
`development_sql()` and `assert_not_sealed()`, and all analysis scripts use them.
The seal is a discipline kept by the code, not a technical lock. The live test is opened
once, after the models are frozen.

## 6. Limits of the simulator

- **Hidden stockouts in the real data.** M5 only records sales. A day with zero sales may
  hide a real stockout at Walmart. The simulator treats M5 sales as the true demand.
- **Launch estimate.** The department average used for launches is computed over the whole
  history, so it contains a small look-ahead. It is the same for every product in the
  department.
- **Assumed behaviour.** Supplier lateness, partial deliveries, expiry, shrink and record
  errors are my assumptions, not measured facts.
- **One policy.** All stockouts depend on the (s, S) ordering policy. Models trained here
  learn this retailer's behaviour.
- **No customer reaction.** Lost sales are gone: no backorders, no substitution, and
  demand does not react to stockouts or to the shop's decisions.
- **One history.** The full run is one random history (seed 42). Experiments during
  development averaged several seeds, but the dataset itself is a single draw.
- **Small sensitivity sample.** The lead-time test used 40 products per category in one
  store, so its absolute numbers differ from the full run.
- **Scope.** Three stores only.