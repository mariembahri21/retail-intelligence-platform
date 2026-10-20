# Retail Intelligence & Stockout Prediction Platform

An analytics platform that shows a retailer what is selling, what is likely to run out of stock, and what inventory decisions to make.

Real demand comes from the M5 (Walmart) dataset. Inventory, supplier deliveries and replenishment are produced by a simulated retailer whose operations evolve day by day, because real retailers do not publish their stock data.

> **Status: work in progress.** Built step by step, in public. See the [project charter](docs/project_charter.md) for the goals, users and scope.

## What exists today

- [x] Project charter, data sources and data dictionary (`docs/`)
- [x] Raw data ingestion into DuckDB (`ingestion/load_m5.py`)
- [x] Automatic data quality checks (`tests/test_raw_data.py`)
- [x] Retailer design: daily cycle, business rules, tables and time periods (`docs/retailer_design.md`)
- [x] Simulation master data (suppliers and product ordering terms)
- [x] Simulation engine, first version (one product)
- [x] Late and partial deliveries
- [x] Losses and stock counts
- [ ] Retail operations simulator
- [ ] Data warehouse with dbt
- [ ] Demand forecasting and stockout prediction
- [ ] Dashboards and daily pipeline

## How to run it

**1. Set up the environment** (Windows PowerShell):

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python simulation/master_data.py
pytest tests/test_master_data.py -v
```

**2. Get the data.** The M5 data is not stored in this repository. Accept the rules of the [M5 Forecasting - Accuracy](https://www.kaggle.com/competitions/m5-forecasting-accuracy) competition on Kaggle (non-commercial use only, see `docs/data_sources.md`), download the files and place `calendar.csv`, `sales_train_evaluation.csv` and `sell_prices.csv` in `data/raw/`.

**3. Build the raw database** (from the project root):

```
python ingestion/load_m5.py
```

This creates `data/processed/retail.duckdb` with three tables in the `raw` schema: `sales` (about 17.8 million rows, one per product, store and day), `calendar` and `prices`. The scope (3 stores) is set in `config.yaml`.

**4. Run the data quality checks:**

```
pytest -v
```

## Project structure

```
config.yaml     project settings (stores, dates, database path)
docs/           charter, data sources, data dictionary, raw schema
ingestion/      scripts that load the raw data
tests/          data quality checks
notebooks/      exploration notebooks
```

## Tech stack

Python, DuckDB, pytest. More will be added as the project grows (dbt, LightGBM, Power BI, Streamlit, Docker).