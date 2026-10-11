# Retail Intelligence & Stockout Prediction Platform — Project Charter

## Problem

Retailers need to decide how much stock to keep for each product, but demand changes from day to day because of seasonality, promotions, holidays, and customer behavior. If a retailer underestimates demand, products can run out of stock, leading to lost sales and unhappy customers. If it orders too much, money is tied up in inventory, warehouse space is wasted, and perishable products may expire before they can be sold. This project aims to help retailers make better inventory decisions by combining demand forecasting, inventory monitoring, and stockout risk prediction in one analytics platform.

## Business Questions
Which products are likely to run out of stock in the next seven days?

How much demand should we expect for each product over the next seven days?

Which products should we reorder first, and how much should we order?

Which products have too much inventory compared with their expected demand?

How do seasonality, holidays, and price changes affect product demand?

How much potential lost sales and excess inventory could we avoid by following the platform's recommendations?
## Users
Store Manager: Monitors inventory risks at store level and decides which products need immediate attention to avoid empty shelves.

Inventory Planner / Buyer: Uses demand forecasts, supplier lead times, and reorder recommendations to decide what to order, how much to order, and when to order it.

Supply Chain Analyst: Monitors inventory performance across stores, evaluates forecast accuracy, investigates recurring stockouts, and identifies opportunities to improve replenishment decisions.
## Success Metrics

Model Metrics :

Forecast accuracy: Reduce forecast error compared with a simple baseline, such as using recent average sales or the same weekday's historical demand.

Stockout detection quality: Identify products at risk of running out before stock reaches zero, while limiting false alarms.

Forecast reliability: Evaluate performance on future, unseen dates and across different products and stores.

Replenishment performance: Assess whether forecast-driven reorder recommendations improve inventory outcomes compared with a baseline replenishment policy.

Business Metrics :

Stockout rate: Reduce the proportion of product-store-days when inventory is unavailable.

Lost sales: Reduce estimated demand that cannot be fulfilled because of insufficient inventory.

Excess inventory: Reduce unnecessary stock while maintaining an acceptable service level.

Inventory efficiency: Improve the balance between product availability, inventory holding costs, and replenishment frequency.

Success will be evaluated through a simulated retail environment and compared with a baseline strategy. Any improvements in lost sales, costs, or stockout rates will be treated as simulated outcomes rather than proven results from a real retailer.

## How the Data Works

The project uses the M5 Forecasting dataset, which contains historical daily sales for Walmart products across multiple stores, along with product hierarchies, calendar events, and selling prices. I will select three stores and approximately 3,000 products to create a manageable but realistic retail scenario. Since the dataset does not provide the complete inventory history, supplier lead times, or actual stockout events needed to evaluate replenishment decisions, I will build a simulated retail operations layer. This layer will generate daily inventory levels, sales-related stock movements, supplier deliveries, purchase orders, and replenishment events according to documented business rules. The simulation makes it possible to test the entire pipeline, from raw data ingestion to inventory recommendations, without claiming access to confidential retailer data.

## Scope and Non-Goals

In Scope

Three simulated stores and approximately 3,000 products, subject to dataset availability.

Historical sales, product, price, and calendar data based on M5.

Simulated daily inventory, stock movements, supplier lead times, and purchase orders.

Automated data ingestion, storage, transformation, and data quality checks.

Demand forecasting and stockout risk prediction.

Reorder recommendations based on forecast demand, available inventory, and replenishment lead times.

BI dashboards for sales trends, inventory risk, forecast performance, and replenishment decisions.

Pipeline orchestration, logging, monitoring, testing, and documentation.

Evaluation of the proposed inventory strategy against a baseline in a simulated environment.

Out of Scope

Access to confidential or live inventory data from an actual retailer.

Real-time streaming or integration with live point-of-sale and warehouse systems.

Automatic placement of purchase orders with real suppliers.

Production deployment for a real retail business.

Guaranteed financial savings or proven reductions in actual stockouts.

A complex optimization system covering every real-world constraint, such as supplier contracts, warehouse capacity, and product expiry.


The initial goal is to deliver a reliable, reproducible end-to-end analytics pipeline that demonstrates how data engineering, forecasting, and business intelligence can support better retail inventory decisions.
