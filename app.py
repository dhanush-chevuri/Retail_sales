import streamlit as st
import pandas as pd
import plotly.express as px
import os
from db.db import DatabaseManager
from etl import ETLPipeline
from utils.logger import setup_logger
from utils.data_gen import generate_mock_data
import time

# --- Setup ---
st.set_page_config(page_title="Retail ETL & Analytics", layout="wide", page_icon="📊")
logger = setup_logger()

# --- Custom Styling ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: red; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #007bff; color: white; }
    </style>
""", unsafe_allow_html=True)

# --- Initialize Managers ---
# Check for environment variables first (Docker setup)
default_host = os.getenv('DB_HOST', 'localhost')
default_user = os.getenv('DB_USER', 'root')
default_pass = os.getenv('DB_PASSWORD', '')
default_name = os.getenv('DB_NAME', 'retail_db')

# --- Sidebar: Configuration ---
with st.sidebar:
    st.header("⚙️ Configuration")
    db_host = st.text_input("MySQL Host", value=default_host)
    db_user = st.text_input("MySQL User", value=default_user)
    db_pass = st.text_input("MySQL Password", value=default_pass, type="password")
    db_name = st.text_input("Database Name", value=default_name)
    
    if st.button("Initialize Database"):
        db_mgr = DatabaseManager(db_host, db_user, db_pass, db_name)
        success, msg = db_mgr.initialize_db()
        if success:
            st.success(msg)
            logger.info("DB Initialization triggered from UI.")
        else:
            st.error(f"Error: {msg}")

db_mgr = DatabaseManager(db_host, db_user, db_pass, db_name)
etl_pipe = ETLPipeline(db_mgr)

# --- App Logic ---
st.title("📊 Retail Sales ETL & Analytics (v2.0)")
st.caption("Enhanced Production Version with Structured Logging & Docker")
st.markdown("---")

tab1, tab2, tab3, tab4 = st.tabs(["📥 Data Ingestion", "🛠️ ETL Pipeline", "📈 Analytics Dashboard", "📜 Logs"])

# --- Tab 1: Data Ingestion ---
with tab1:
    st.subheader("Data Sources")
    col1, col2 = st.columns(2)
    with col1:
        st.write("### File Upload")
        uploaded_file = st.file_uploader("Upload CSV or JSON", type=["csv", "json"])
    with col2:
        st.write("### API Fetch")
        if st.button("Simulate API Fetch"):
            with st.spinner("Fetching data..."):
                time.sleep(1)
                raw_df = generate_mock_data(100)
                st.session_state['last_fetched'] = raw_df
                st.success(f"Fetched {len(raw_df)} records.")

    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_json(uploaded_file)
            st.session_state['last_fetched'] = df
            st.success(f"Loaded {len(df)} records from {uploaded_file.name}")
        except Exception as e:
            st.error(f"Error loading file: {e}")

    if 'last_fetched' in st.session_state:
        st.write("### Raw Data Preview")
        st.dataframe(st.session_state['last_fetched'].head(10))
        if st.button("Load into Bronze Layer"):
            success, msg = etl_pipe.load_bronze(st.session_state['last_fetched'])
            st.success(msg) if success else st.error(msg)

# --- Tab 2: ETL Pipeline ---
with tab2:
    st.subheader("Pipeline Controls")
    if st.button("🚀 Run Medallion ETL Pipeline"):
        with st.spinner("Processing Bronze → Silver → Gold..."):
            success, msgs = etl_pipe.run_pipeline()
            if success:
                for msg in msgs: st.write(f"✅ {msg}")
                st.success("Full Pipeline Complete!")
            else:
                st.error(f"Pipeline Failed: {msgs}")
    
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.write("#### 🟤 Bronze Data")
        try:
            st.dataframe(pd.read_sql("SELECT * FROM bronze_sales LIMIT 5", db_mgr.get_engine()))
        except: st.warning("Bronze table empty.")
    with c2:
        st.write("#### ⚪ Silver Data")
        try:
            st.dataframe(pd.read_sql("SELECT * FROM silver_sales LIMIT 5", db_mgr.get_engine()))
        except: st.warning("Silver table empty.")

# --- Tab 3: Analytics Dashboard ---
with tab3:
    try:
        engine = db_mgr.get_engine()
        df_store = pd.read_sql("SELECT * FROM gold_sales_by_store", engine)
        df_cat = pd.read_sql("SELECT * FROM gold_sales_by_category", engine)
        df_date = pd.read_sql("SELECT * FROM gold_sales_by_date", engine)
        
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("Total Revenue", f"${df_store['total_sales'].sum():,.2f}")
        kpi2.metric("Total Transactions", f"{df_store['total_orders'].sum():,}")
        kpi3.metric("Top Store", df_store.loc[df_store['total_sales'].idxmax()]['store_id'])

        v1, v2 = st.columns(2)
        v1.plotly_chart(px.bar(df_store, x='store_id', y='total_sales', title="Revenue by Store"), use_container_width=True)
        v2.plotly_chart(px.pie(df_cat, values='total_sales', names='product_category', title="Sales by Category"), use_container_width=True)
        st.plotly_chart(px.line(df_date.sort_values('order_date'), x='order_date', y='total_sales', title="Daily Sales Trend"), use_container_width=True)
    except:
        st.info("Run the ETL Pipeline to generate analytics.")

# --- Tab 4: Logs ---
with tab4:
    st.subheader("ETL Logs")
    if st.button("Refresh Logs"):
        if os.path.exists("logs/etl.log"):
            with open("logs/etl.log", "r") as f:
                log_content = f.readlines()
                st.text_area("Live Log Output", value="".join(log_content[-20:]), height=400)
        else:
            st.warning("No log file found yet.")
