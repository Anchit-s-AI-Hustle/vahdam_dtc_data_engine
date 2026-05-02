# VAHDAM DTC Analytics Engine

A local DuckDB analytics layer for VAHDAM's direct-to-consumer tea business — combining Shopify raw exports (Matrixify), Shopify Analytics reports, Klaviyo email/SMS data, and WebEngage CDP events into a single queryable database.

---

## Folder Structure

```
vahdam-dtc-data-engine/
├── vahdam_dtc.duckdb           # Main DuckDB database (4 schemas, 46 tables)
├── VAHDAM_DuckDB_DDL.sql       # Full DDL — run once to create all schemas & tables
├── run_all.py                  # Master ingestion runner
│
├── ingest/
│   ├── ingest_matrixify.py         # Loads Matrixify (Shopify raw) CSVs
│   ├── ingest_shopify_analytics.py # Loads Shopify Analytics CSVs
│   ├── ingest_klaviyo.py           # Loads Klaviyo CSV / JSON exports
│   └── ingest_webengage.py         # Loads WebEngage CSVs + rebuilds event_summary
│
├── queries/
│   └── metrics.sql             # All 15 core DTC metrics + bonus LTV by market
│
├── data/
│   ├── matrixify/              # Drop Matrixify CSV exports here
│   ├── shopify_analytics/      # Drop Shopify Analytics CSV exports here
│   ├── klaviyo/                # Drop Klaviyo CSV / JSON exports here
│   └── webengage/              # Drop WebEngage CSV exports here
│
└── logs/                       # Ingest run logs (auto-created)
```

---

## Setup

### 1. Install dependencies

```bash
python -m pip install duckdb pandas
```

### 2. Create the database

The database (`vahdam_dtc.duckdb`) is created automatically by running the DDL script. If it doesn't exist yet:

```bash
python _init_db.py
```

Or use the DuckDB CLI:

```bash
duckdb vahdam_dtc.duckdb < VAHDAM_DuckDB_DDL.sql
```

---

## Loading Data

### Add new data

1. Export CSVs from Matrixify / Shopify Admin / Klaviyo / WebEngage
2. Drop files into the matching `data/[source]/` folder using the exact table name:
   - `data/matrixify/orders.csv`, `customers.csv`, `products.csv`, etc.
   - `data/shopify_analytics/revenue_metrics.csv`, `traffic_metrics.csv`, etc.
   - `data/klaviyo/profiles.csv`, `campaigns.csv`, `events.csv`, etc.
   - `data/webengage/user_profiles.csv`, `events.csv`, etc.
3. Run the ingestion:

```bash
# Load all sources
python run_all.py

# Load a single source
python run_all.py --source matrixify
python run_all.py --source klaviyo
python run_all.py --source shopify_analytics
python run_all.py --source webengage
```

Logs are written to `logs/ingest_YYYYMMDD_HHMMSS.log`.

---

## Running Queries

### Interactive DuckDB shell

```bash
duckdb vahdam_dtc.duckdb
.read queries/metrics.sql
```

### Run a single metric

```bash
duckdb vahdam_dtc.duckdb "SELECT * FROM matrixify.orders LIMIT 10"
```

### From Python

```python
import duckdb
con = duckdb.connect("vahdam_dtc.duckdb")
df = con.execute("SELECT * FROM matrixify.orders LIMIT 100").df()
```

---

## The 15 Core Metrics

| # | Metric | Description |
|---|--------|-------------|
| 1 | **Net Revenue by Market** | Gross sales, discounts, net sales, AOV split across US / UK / IN / RoW |
| 2 | **New vs Returning Revenue Split** | Monthly revenue and order count for new vs returning customers |
| 3 | **LTV:CAC Ratio by Channel** | Lifetime value divided by customer acquisition cost, flagged if below 3:1 |
| 4 | **Repeat Purchase Rate (90-day)** | % of first-time buyers per cohort who placed a 2nd order within 90 days |
| 5 | **Gross Margin %** | (Price − COGS) / Price, by month and product type |
| 6 | **CAC by Channel** | Sessions, new customers, and conversion rate from Shopify acquisition report |
| 7 | **Email Revenue %** | Klaviyo-attributed revenue as % of total Shopify net sales, campaign breakdown |
| 8 | **AOV Trend (monthly)** | Monthly average order value with MoM % change, flagged on >5% drops |
| 9 | **Checkout Conversion Rate** | Weekly funnel: Product Viewed → Add to Cart → Checkout → Order |
| 10 | **Subscription Mix %** | Subscription vs one-time revenue split per month |
| 11 | **Cohort Retention (30/60/90-day)** | % of acquisition cohort still purchasing at 30, 60, 90 days |
| 12 | **Time to 2nd Purchase** | Avg and median days between order 1 and 2, by market and channel |
| 13 | **Churn Risk Distribution** | Klaviyo predicted churn buckets: low / medium / high / winback |
| 14 | **At-Risk Revenue** | SUM of predicted 1-year CLV for high + winback churn profiles |
| 15 | **Product Repeat Rate** | % of first-time buyers of each SKU who repurchased any product within 90 days |
| B | **LTV by Market** | Avg/median lifetime value, order count, AOV per geographic market |

---

## Schema Overview

| Schema | Tables | Source | Strategy |
|--------|--------|--------|----------|
| `matrixify` | 20 | Matrixify Shopify exports | Upsert by `id` |
| `shopify_analytics` | 13 | Shopify Analytics reports | Append + dedup on `(report_date, report_period)` |
| `klaviyo` | 9 | Klaviyo CSV/JSON | Upsert by entity ID; events append-only |
| `webengage` | 4 | WebEngage CSV | Upsert; `event_summary` rebuilt after each events load |

**Total: 4 schemas, 46 tables**

All tables include a `_loaded_at TIMESTAMP` audit column.

---

## Next Steps

- **Connect a BI tool** — DuckDB supports direct connection from Tableau, Metabase, Evidence.dev, and Superset via the DuckDB connector or JDBC driver
- **Schedule ingestion** — run `python run_all.py` nightly via Windows Task Scheduler or a cron job
- **Add more metrics** — extend `queries/metrics.sql` with RFM segmentation, promo effectiveness, or inventory-linked margin analysis
- **Shopify GraphQL sync** — replace Matrixify CSV exports with a live GraphQL-to-DuckDB pipeline for near-real-time data
- **dbt integration** — wrap the metric queries as dbt models for version-controlled, tested transformations
