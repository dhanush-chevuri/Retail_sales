import pandas as pd
from sqlalchemy import text, types
from datetime import datetime
from utils.logger import setup_logger

logger = setup_logger()

def clean_sales_data(df):
    """
    Pure transformation logic for sales data.
    Can be tested independently of any database.
    """
    if df.empty:
        return df

    # 1. Basic Cleaning
    # Remove ingestion_timestamp and id if they exist, and ensure we have a fresh copy
    df_clean = df.drop(columns=['id', 'ingestion_timestamp'], errors='ignore').copy()
    
    # Handle missing unit_price
    initial_count = len(df_clean)
    df_clean['unit_price'] = pd.to_numeric(df_clean['unit_price'], errors='coerce')
    df_clean = df_clean.dropna(subset=['unit_price'])
    if len(df_clean) < initial_count:
        logger.warning(f"Dropped {initial_count - len(df_clean)} rows with missing unit_price.")
    
    # Fix negative quantity
    pre_neg_count = len(df_clean)
    df_clean['quantity_sold'] = pd.to_numeric(df_clean['quantity_sold'], errors='coerce')
    df_clean = df_clean[df_clean['quantity_sold'] > 0]
    if len(df_clean) < pre_neg_count:
        logger.warning(f"Dropped {pre_neg_count - len(df_clean)} rows with invalid (negative/zero) quantity.")
    
    # Fix date formats
    pre_date_count = len(df_clean)
    df_clean['order_date'] = pd.to_datetime(df_clean['order_date'], errors='coerce')
    df_clean = df_clean.dropna(subset=['order_date'])
    if len(df_clean) < pre_date_count:
        logger.warning(f"Dropped {pre_date_count - len(df_clean)} rows with invalid date formats.")
    
    # 2. Derived Columns
    df_clean['total_amount'] = df_clean['quantity_sold'] * df_clean['unit_price']
    df_clean['order_month'] = df_clean['order_date'].dt.month
    df_clean['order_day'] = df_clean['order_date'].dt.day
    
    # 3. Remove Duplicates
    df_clean = df_clean.drop_duplicates(subset=['order_id'], keep='last')
    
    return df_clean

class ETLPipeline:
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.engine = db_manager.get_engine()

    def load_bronze(self, df):
        """Loads raw data into the bronze table, clearing previous data first."""
        try:
            logger.info(f"ETL - EXTRACT: Starting load into bronze_sales ({len(df)} rows).")
            
            # Truncate table to remove previous data while keeping schema
            with self.engine.connect() as conn:
                conn.execute(text("TRUNCATE TABLE bronze_sales"))
                conn.commit()
                
            # Ensure columns match schema
            df_bronze = df.astype(str)
            df_bronze.to_sql('bronze_sales', con=self.engine, if_exists='append', index=False)
            logger.info("ETL - EXTRACT: Complete.")
            return True, "Bronze table cleared and new data loaded successfully."
        except Exception as e:
            logger.error(f"ETL - EXTRACT: Failed. Error: {e}")
            return False, str(e)

    def transform_silver(self):
        """Cleans and transforms data from bronze to silver."""
        try:
            logger.info("ETL - TRANSFORM (Silver): Starting...")
            # 1. Read from Bronze
            df_bronze = pd.read_sql("SELECT * FROM bronze_sales", con=self.engine)
            
            if df_bronze.empty:
                logger.info("ETL - TRANSFORM (Silver): No data to process.")
                return True, "No data in Bronze to transform."

            # 2. Use the dedicated cleaning function
            df_clean = clean_sales_data(df_bronze)
            
            # 3. Load to Silver
            logger.info(f"ETL - LOAD (Silver): Saving {len(df_clean)} records.")
            dtypes = {
                'order_id': types.VARCHAR(50),
                'store_id': types.VARCHAR(50),
                'product_id': types.VARCHAR(50),
                'product_category': types.VARCHAR(100)
            }
            df_clean.to_sql('silver_sales', con=self.engine, if_exists='replace', index=False, dtype=dtypes)
            
            # Re-add primary key constraint
            with self.engine.connect() as conn:
                conn.execute(text("ALTER TABLE silver_sales ADD PRIMARY KEY (order_id)"))
                conn.commit()

            logger.info("ETL - TRANSFORM (Silver): Complete.")
            return True, f"Silver transformation complete. {len(df_clean)} rows processed."
        except Exception as e:
            logger.error(f"ETL - TRANSFORM (Silver): Failed. Error: {e}")
            return False, str(e)

    def transform_gold(self):
        """Aggregates data from silver to gold."""
        try:
            logger.info("ETL - TRANSFORM (Gold): Starting aggregation...")
            df_silver = pd.read_sql("SELECT * FROM silver_sales", con=self.engine)
            
            if df_silver.empty:
                logger.info("ETL - TRANSFORM (Gold): No data to process.")
                return True, "No data in Silver to aggregate."

            # Aggregation 1: By Store
            gold_store = df_silver.groupby('store_id').agg(
                total_sales=('total_amount', 'sum'),
                total_orders=('order_id', 'count')
            ).reset_index()
            gold_store.to_sql('gold_sales_by_store', con=self.engine, if_exists='replace', index=False, dtype={'store_id': types.VARCHAR(50)})

            # Aggregation 2: By Category
            gold_cat = df_silver.groupby('product_category').agg(
                total_sales=('total_amount', 'sum'),
                total_orders=('order_id', 'count')
            ).reset_index()
            gold_cat.to_sql('gold_sales_by_category', con=self.engine, if_exists='replace', index=False, dtype={'product_category': types.VARCHAR(100)})

            # Aggregation 3: By Date
            df_silver['date_only'] = pd.to_datetime(df_silver['order_date']).dt.date
            gold_date = df_silver.groupby('date_only').agg(
                total_sales=('total_amount', 'sum'),
                total_orders=('order_id', 'count')
            ).reset_index()
            gold_date.rename(columns={'date_only': 'order_date'}, inplace=True)
            gold_date.to_sql('gold_sales_by_date', con=self.engine, if_exists='replace', index=False)

            logger.info("ETL - TRANSFORM (Gold): Complete.")
            return True, "Gold transformation complete."
        except Exception as e:
            logger.error(f"ETL - TRANSFORM (Gold): Failed. Error: {e}")
            return False, str(e)

    def run_pipeline(self, raw_df=None):
        """Runs the full E2E pipeline."""
        results = []
        logger.info("ETL PIPELINE: Full run started.")
        
        if raw_df is not None:
            success, msg = self.load_bronze(raw_df)
            results.append(f"Bronze: {msg}")
            if not success: 
                logger.error("ETL PIPELINE: Aborted at Bronze stage.")
                return False, results
            
        success, msg = self.transform_silver()
        results.append(f"Silver: {msg}")
        if not success: 
            logger.error("ETL PIPELINE: Aborted at Silver stage.")
            return False, results
        
        success, msg = self.transform_gold()
        results.append(f"Gold: {msg}")
        if not success: 
            logger.error("ETL PIPELINE: Aborted at Gold stage.")
            return False, results
        
        logger.info("ETL PIPELINE: Successfully finished.")
        return True, results
