# Retail ETL & Analytics Project - Complete Context

## Project Summary
A Python-based ETL (Extract-Transform-Load) pipeline with a web dashboard for retail sales data processing and analytics. Uses the medallion architecture (Bronze → Silver → Gold) to progressively clean, transform, and aggregate sales data.

---

## Architecture Overview

### Medallion Pattern (Three-Layer Data Architecture)
```
Raw Data (CSV/JSON/API) 
    ↓
[BRONZE LAYER] - Raw ingestion, minimal processing
    ↓ (clean, validate, derive columns)
[SILVER LAYER] - Cleaned, transformed, deduplicated data
    ↓ (aggregate by store, category, date)
[GOLD LAYER] - Business-ready aggregations for analytics
    ↓
Streamlit Dashboard (KPIs, Charts)
```

### Key Components
1. **Data Source**: CSV/JSON file uploads or simulated API calls
2. **Storage**: MySQL database with 3 schema layers
3. **Processing**: Pandas DataFrames for transformation
4. **UI**: Streamlit web app with tabs for ingestion, pipeline control, analytics, logs
5. **Testing**: pytest unit tests + headless integration runner

---

## Technology Stack & Why

| Tech | Purpose | Why This Choice |
|------|---------|-----------------|
| **Python** | Core language | Industry standard for ETL and data processing |
| **Streamlit** | Web dashboard UI | Fast development, zero HTML/CSS needed, data-centric |
| **MySQL** | Data persistence | Relational DB, common in analytics, integrates with pandas |
| **SQLAlchemy** | ORM/DB abstraction | Portability, works with pandas `.to_sql()` |
| **pandas** | Data transformation | Standard for tabular ETL, excellent data cleaning/aggregation |
| **plotly** | Interactive charts | Rich visualizations inside Streamlit |
| **pytest** | Unit testing | Lightweight, standard, simple test discovery |
| **mysql-connector-python** | MySQL driver | Pure Python, no external dependencies |

---

## Project Structure

```
retail/
├── app.py                    # Streamlit dashboard (UI/orchestration)
├── db.py                     # DatabaseManager class (MySQL setup & tables)
├── etl.py                    # ETLPipeline & clean_sales_data() (core transformation)
├── test_pipeline.py          # Headless integration runner
├── requirements.txt          # Python dependencies
├── logs/                     # ETL execution logs (auto-generated)
├── tests/
│   ├── __init__.py
│   └── test_transform.py     # Unit tests for clean_sales_data()
└── utils/
    ├── __init__.py
    ├── logger.py             # Logging setup
    └── data_gen.py           # Mock data generator
```

---

## Data Flow & Processing Steps

### Step 1: Extract (Bronze Layer)
```python
# Input: CSV/JSON file or mock API call
# Output: raw_df loaded into MySQL bronze_sales table

Raw Fields: order_id, order_date, store_id, product_id, 
            product_category, quantity_sold, unit_price, 
            ingestion_timestamp (auto)
```

**Code**: `app.py` → File Upload / API Simulate button → `etl.py:load_bronze()`

### Step 2: Transform (Bronze → Silver)
```python
def clean_sales_data(df):
    # 1. Data type conversion: strings → numeric/datetime
    # 2. Drop invalid rows:
    #    - Missing unit_price
    #    - quantity_sold <= 0
    #    - Invalid date formats
    # 3. Derive columns:
    #    - total_amount = quantity_sold * unit_price
    #    - order_month = extract month from order_date
    #    - order_day = extract day from order_date
    # 4. Remove duplicates on order_id (keep last)
    return cleaned_df
```

**Code**: `etl.py:transform_silver()` → calls `clean_sales_data()` → saves to `silver_sales` table

### Step 3: Aggregate (Silver → Gold)
```python
# Creates 3 aggregation tables:
1. gold_sales_by_store:      GROUP BY store_id
2. gold_sales_by_category:   GROUP BY product_category
3. gold_sales_by_date:       GROUP BY order_date

Each includes: total_sales (SUM), total_orders (COUNT)
```

**Code**: `etl.py:transform_gold()` → aggregates silver_sales → saves to 3 gold tables

### Step 4: Dashboard
```python
# Display:
- KPIs: Total Revenue, Total Transactions, Top Store
- Charts: Bar (Revenue by Store), Pie (Sales by Category), 
          Line (Daily Sales Trend)
- Live logs from etl.log
```

**Code**: `app.py` → Tab 3 (Analytics Dashboard) → reads gold tables → plotly charts

---

## Key Files Explained

### `app.py` - Streamlit Web Interface
**Purpose**: User-facing dashboard for data ingestion, pipeline orchestration, analytics, logs

**Main Sections**:
- **Config Sidebar**: DB connection parameters (host, user, password, database name)
  - Supports env vars: `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`
  - Button: Initialize Database
- **Tab 1 - Data Ingestion**:
  - CSV/JSON file upload
  - Mock API fetch (generates 100 sample records)
  - Button: Load into Bronze Layer
- **Tab 2 - ETL Pipeline**:
  - Button: Run Medallion ETL Pipeline (Bronze→Silver→Gold)
  - Preview bronze_sales and silver_sales tables
- **Tab 3 - Analytics Dashboard**:
  - KPIs (Total Revenue, Total Transactions, Top Store)
  - 3 interactive charts (bar, pie, line)
  - Runs after pipeline completes
- **Tab 4 - Logs**:
  - Display last 20 lines of `logs/etl.log`
  - Button: Refresh Logs

**Dependencies**: DatabaseManager, ETLPipeline, logger, mock data generator, streamlit/pandas/plotly

---

### `db.py` - Database Manager
**Purpose**: MySQL connection, database initialization, table schema creation

**DatabaseManager Class**:
- `__init__()`: Accepts host, user, password, database (or reads from env vars)
- `initialize_db()`: Creates database and calls `create_tables()`, logs errors
- `create_tables()`: Executes SQL CREATE TABLE IF NOT EXISTS for:
  - **bronze_sales**: All fields as VARCHAR (raw)
  - **silver_sales**: Proper types (DATETIME, INT, FLOAT), order_id is PRIMARY KEY
  - **gold_sales_by_store**: store_id PRIMARY KEY, totals
  - **gold_sales_by_category**: product_category PRIMARY KEY, totals
  - **gold_sales_by_date**: order_date PRIMARY KEY, totals
- `get_engine()`: Returns SQLAlchemy engine for pandas integration
- `get_connection_string()`: Builds MySQL connection URI

**Key Design**:
- Bronze is intentionally string-typed (raw layer)
- Silver enforces data types (clean layer)
- Gold is pre-aggregated for fast queries

---

### `etl.py` - ETL Pipeline
**Purpose**: Data cleaning, transformation, aggregation logic

**clean_sales_data(df) Function**:
Standalone, testable transformation:
1. Drop technical columns (id, ingestion_timestamp)
2. Convert unit_price to numeric, drop NaN rows
3. Convert quantity_sold to numeric, drop values ≤ 0
4. Convert order_date to datetime, drop invalid dates
5. Calculate total_amount = quantity_sold × unit_price
6. Extract order_month, order_day
7. Drop duplicate order_ids (keep last)

**ETLPipeline Class**:
- `__init__(db_manager)`: Accepts DatabaseManager instance
- `load_bronze(df)`: TRUNCATE bronze_sales, load new raw data (E phase)
- `transform_silver()`: Read bronze → clean_sales_data() → save silver_sales (T phase)
- `transform_gold()`: Read silver → GROUP BY aggregations → save 3 gold tables (L phase)
- `run_pipeline(raw_df=None)`: Orchestrates full E→T→L, returns (success_bool, messages_list)

**Logging**: Each step logs via utils.logger (INFO for success, ERROR for failures)

---

### `tests/test_transform.py` - Unit Tests
**Purpose**: Validate clean_sales_data() in isolation (no DB required)

**Test Cases**:
1. `test_missing_unit_price()`: Assert NaN prices are dropped
2. `test_negative_quantity()`: Assert quantity ≤ 0 is dropped
3. `test_date_format_conversion()`: Assert dates converted to datetime
4. `test_total_amount_calculation()`: Assert quantity × price and month/day extraction

**Run**: `pytest` from repo root

---

### `test_pipeline.py` - Integration Test Runner
**Purpose**: Headless execution (no UI), end-to-end validation

**Workflow**:
1. Initialize DB with root credentials
2. Generate 100 mock records
3. Run full ETL pipeline
4. Print gold_sales_by_store report
5. Log all steps

**Run**: `python test_pipeline.py` from repo root

---

### `utils/logger.py` - Logging Setup
**Purpose**: Structured logging for ETL operations

**Features**:
- Writes to `logs/etl.log`
- Console + file handlers
- Timestamps, log levels (INFO, WARNING, ERROR)

---

### `utils/data_gen.py` - Mock Data Generator
**Purpose**: Generates synthetic sales records for testing/demo

**Output Schema**:
```
order_id, order_date, store_id, product_id, product_category,
quantity_sold, unit_price
```

**Intentional "Mess"**: Includes some invalid data (negative quantities, missing prices, bad dates) for testing cleaning logic

---

## Database Schema

### Bronze (Raw)
| Column | Type |
|--------|------|
| id | INT PRIMARY KEY AUTO_INCREMENT |
| order_id | VARCHAR(50) |
| order_date | VARCHAR(50) |
| store_id | VARCHAR(50) |
| product_id | VARCHAR(50) |
| product_category | VARCHAR(100) |
| quantity_sold | VARCHAR(50) |
| unit_price | VARCHAR(50) |
| ingestion_timestamp | TIMESTAMP DEFAULT CURRENT_TIMESTAMP |

### Silver (Cleaned)
| Column | Type |
|--------|------|
| order_id | VARCHAR(50) PRIMARY KEY |
| order_date | DATETIME |
| store_id | VARCHAR(50) |
| product_id | VARCHAR(50) |
| product_category | VARCHAR(100) |
| quantity_sold | INT |
| unit_price | FLOAT |
| total_amount | FLOAT |
| order_month | INT |
| order_day | INT |
| transformation_timestamp | TIMESTAMP DEFAULT CURRENT_TIMESTAMP |

### Gold (Aggregated)
**gold_sales_by_store**
| Column | Type |
|--------|------|
| store_id | VARCHAR(50) PRIMARY KEY |
| total_sales | FLOAT |
| total_orders | INT |
| last_updated | TIMESTAMP |

**gold_sales_by_category**
| Column | Type |
|--------|------|
| product_category | VARCHAR(100) PRIMARY KEY |
| total_sales | FLOAT |
| total_orders | INT |
| last_updated | TIMESTAMP |

**gold_sales_by_date**
| Column | Type |
|--------|------|
| order_date | DATE PRIMARY KEY |
| total_sales | FLOAT |
| total_orders | INT |
| last_updated | TIMESTAMP |

---

## How to Run

### Prerequisites
- Python 3.8+
- MySQL server running (default: localhost, root user)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure MySQL (Optional)
Set environment variables or use Streamlit sidebar:
```bash
export DB_HOST=localhost
export DB_USER=root
export DB_PASSWORD=12345
export DB_NAME=retail_db
```

### 3. Run Streamlit Dashboard
```bash
streamlit run app.py
```
Then in browser: `http://localhost:8501`

**First Time Setup**:
- Go to sidebar, fill in DB credentials
- Click "Initialize Database"

### 4. Load Data
- Tab 1: Upload CSV/JSON OR click "Simulate API Fetch"
- Click "Load into Bronze Layer"

### 5. Run Pipeline
- Tab 2: Click "🚀 Run Medallion ETL Pipeline"
- Wait for completion message

### 6. View Analytics
- Tab 3: See KPIs and charts
- Tab 4: View logs

### 7. Run Tests
```bash
# Unit tests
pytest

# Integration test (headless)
python test_pipeline.py
```

---

## Design Decisions & Trade-offs

### Why Bronze as Raw Strings?
- Captures ingestion as-is (no data loss)
- Easy to inspect raw data quality issues
- Separation of concerns: ingestion ≠ cleaning

### Why Medallion Architecture?
- Clear data quality progression
- Easy to debug which layer failed
- Enables independent table queries
- Standard in modern data warehouses

### Why Pandas (not SQL)?
- More flexible transformations (Python logic)
- Better for ad-hoc validation
- Easier testing (no DB dependency)
- Single tool for cleaning + aggregation

### Why Streamlit (not Flask)?
- Fast prototyping (no HTML/CSS)
- Built-in session state
- Native pandas/plotly support
- Good for demos

### Why MySQL (not SQLite)?
- Explicit choice in connection strings
- Aligns with enterprise retail systems
- More scalable for larger datasets

### Why Pytest (not unittest)?
- Simpler syntax, better discovery
- Fixtures over setUp/tearDown
- No boilerplate required

---

## Current Limitations & Future Improvements

### Limitations
1. **No incremental loading**: Bronze truncates each run (loses history)
2. **No error recovery**: Failed rows are just logged, not stored
3. **No data validation schemas**: Only basic type checking
4. **Single-machine only**: No distributed processing
5. **No scheduling**: Manual pipeline execution via UI button

### Future Enhancements
- Add Apache Airflow for scheduling
- Implement data lineage/audit trail
- Add data quality checks (Great Expectations)
- Use Spark for larger datasets
- Add Kafka for real-time streaming
- Implement SLA monitoring

---

## Quick Troubleshooting

| Issue | Solution |
|-------|----------|
| `Connection refused` | Ensure MySQL server is running on localhost:3306 |
| `Access denied` | Check DB credentials in sidebar or env vars |
| `Table already exists` | Tables are created with IF NOT EXISTS, safe to reinit |
| `Dropped too many rows` | Check data quality; clean_sales_data() is strict by design |
| `Logs not appearing` | Check `logs/` directory; ensure write permissions |
| `Tests fail` | Run `pytest -v` for detailed error messages |

---

## Summary for AI Context

This is a **Python ETL demo project** that:
1. Ingests raw sales data (CSV/JSON/API) into **MySQL Bronze layer**
2. Cleans & transforms to **Silver layer** (type conversion, validation, derivation)
3. Aggregates to **Gold layer** (store/category/date summaries)
4. Exposes results via **Streamlit dashboard** with KPIs and charts
5. Uses **pandas** for transformations, **MySQL** for storage, **pytest** for testing
6. Follows **medallion architecture** for data quality progression
7. Includes **unit tests**, **integration runner**, and **structured logging**

**Run**: `streamlit run app.py` → Upload data → Click ETL button → View analytics

**Test**: `pytest` or `python test_pipeline.py`
