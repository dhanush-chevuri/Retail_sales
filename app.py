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

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📥 Data Ingestion", "🛠️ ETL Pipeline", "📈 Analytics Dashboard", "📜 Logs", "🗑️ Dropped Records"])

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

        # Get raw silver data for dynamic filtering
        df_silver = pd.read_sql("SELECT * FROM silver_sales", engine)

        if df_silver.empty:
            st.info("No silver data available. Run the ETL Pipeline first.")
        else:
            # Filters Section
            st.subheader("🔍 Filters")
            col1, col2, col3 = st.columns(3)

            with col1:
                # Store filter
                all_stores = ["All"] + sorted(df_silver['store_id'].unique().tolist())
                selected_store = st.selectbox("Filter by Store", all_stores)

            with col2:
                # Category filter
                all_categories = ["All"] + sorted(df_silver['product_category'].unique().tolist())
                selected_category = st.selectbox("Filter by Category", all_categories)

            with col3:
                # Date range filter
                min_date = pd.to_datetime(df_silver['order_date']).min().date()
                max_date = pd.to_datetime(df_silver['order_date']).max().date()
                date_range = st.date_input(
                    "Date Range",
                    value=(min_date, max_date),
                    min_value=min_date,
                    max_value=max_date
                )

            # Apply filters to raw data
            filtered_df = df_silver.copy()

            if selected_store != "All":
                filtered_df = filtered_df[filtered_df['store_id'] == selected_store]

            if selected_category != "All":
                filtered_df = filtered_df[filtered_df['product_category'] == selected_category]

            if date_range and len(date_range) == 2:
                start_date, end_date = date_range
                filtered_df = filtered_df[
                    (pd.to_datetime(filtered_df['order_date']).dt.date >= start_date) &
                    (pd.to_datetime(filtered_df['order_date']).dt.date <= end_date)
                ]

            # Create dynamic aggregations from filtered data
            if not filtered_df.empty:
                # Store aggregation
                df_store_filtered = filtered_df.groupby('store_id').agg({
                    'total_amount': 'sum',
                    'order_id': 'count'
                }).reset_index().rename(columns={
                    'total_amount': 'total_sales',
                    'order_id': 'total_orders'
                })

                # Category aggregation
                df_cat_filtered = filtered_df.groupby('product_category').agg({
                    'total_amount': 'sum'
                }).reset_index().rename(columns={'total_amount': 'total_sales'})

                # Date aggregation
                df_date_filtered = filtered_df.groupby(filtered_df['order_date'].dt.date).agg({
                    'total_amount': 'sum'
                }).reset_index().rename(columns={
                    'order_date': 'order_date',
                    'total_amount': 'total_sales'
                })

                st.markdown("---")

                # KPIs from filtered data
                kpi1, kpi2, kpi3 = st.columns(3)
                kpi1.metric("Total Revenue", f"${df_store_filtered['total_sales'].sum():,.2f}")
                kpi2.metric("Total Transactions", f"{df_store_filtered['total_orders'].sum():,}")
                if not df_store_filtered.empty:
                    top_store = df_store_filtered.loc[df_store_filtered['total_sales'].idxmax()]['store_id']
                    kpi3.metric("Top Store", top_store)
                else:
                    kpi3.metric("Top Store", "N/A")

                # Charts from filtered data
                v1, v2 = st.columns(2)
                if not df_store_filtered.empty:
                    v1.plotly_chart(px.bar(df_store_filtered, x='store_id', y='total_sales', title="Revenue by Store"), use_container_width=True)
                else:
                    v1.info("No store data for selected filters")

                if not df_cat_filtered.empty:
                    v2.plotly_chart(px.pie(df_cat_filtered, values='total_sales', names='product_category', title="Sales by Category"), use_container_width=True)
                else:
                    v2.info("No category data for selected filters")

                # Date trend chart
                if not df_date_filtered.empty:
                    st.plotly_chart(px.line(df_date_filtered.sort_values('order_date'), x='order_date', y='total_sales', title="Daily Sales Trend"), use_container_width=True)
                else:
                    st.info("No date data for selected filters")
            else:
                st.warning("No data matches the selected filters. Try adjusting your filter criteria.")

    except Exception as e:
        st.error(f"Error loading analytics: {e}")
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

# --- Tab 5: Dropped Records ---
with tab5:
    st.subheader("🗑️ Dropped Records Analysis")
    st.write("Records that were rejected during data cleaning with reasons:")

    try:
        engine = db_mgr.get_engine()
        dropped_df = pd.read_sql("SELECT * FROM dropped_sales", engine)

        if not dropped_df.empty:
            # Summary statistics
            st.write("### Summary")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Dropped Records", len(dropped_df))
            with col2:
                st.metric("Most Common Reason", dropped_df['drop_reason'].mode().iloc[0] if len(dropped_df) > 0 else "N/A")
            with col3:
                st.metric("Unique Reasons", dropped_df['drop_reason'].nunique())

            # Reason distribution
            st.write("### Drop Reasons Distribution")
            reason_counts = dropped_df['drop_reason'].value_counts()
            st.bar_chart(reason_counts)

            # Detailed table
            st.write("### Detailed Dropped Records")
            st.dataframe(dropped_df, use_container_width=True)

            # Export option
            csv = dropped_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Dropped Records CSV",
                data=csv,
                file_name="dropped_records.csv",
                mime="text/csv"
            )
        else:
            st.info("No dropped records found. Run the ETL pipeline to see data quality issues.")

    except Exception as e:
        st.warning("Dropped records table not found. Run the ETL pipeline first.")
        st.write(f"Error: {e}")
