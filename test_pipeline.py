from db.db import DatabaseManager
from etl import ETLPipeline
from utils.logger import setup_logger
from utils.data_gen import generate_mock_data
import pandas as pd
import os

def run_test():
    # Setup logger
    logger = setup_logger()
    logger.info("INTEGRATION TEST: Starting Headless ETL Run...")
    
    # Initialize DB (Using root with password '12345' as seen in project settings)
    db_mgr = DatabaseManager(user='root', password='12345') 
    success, msg = db_mgr.initialize_db()
    if not success:
        logger.error(f"INTEGRATION TEST: Database Initialization Failed. Error: {msg}")
        return
    
    # 1. Generate Mock Data (Extraction Stage)
    logger.info("INTEGRATION TEST: Phase 1 - Generating 100 messy records...")
    mock_df = generate_mock_data(100)
    
    # 2. Run ETL Pipeline (Transformation & Loading Stage)
    etl = ETLPipeline(db_mgr)
    success, results = etl.run_pipeline(mock_df)
    
    if success:
        logger.info("INTEGRATION TEST: ETL Pipeline executed successfully!")
        for r in results:
            print(f"- {r}")
            
        # 3. Final Verification (Aggregation Stats)
        engine = db_mgr.get_engine()
        store_report = pd.read_sql("SELECT * FROM gold_sales_by_store", engine)
        
        print("\n" + "="*40)
        print("          GOLD LAYER REPORT           ")
        print("="*40)
        print(store_report)
        print("="*40)
        
        logger.info("INTEGRATION TEST: Complete.")
    else:
        logger.error(f"INTEGRATION TEST: ETL Pipeline Failed at some stage. Status: {results}")

if __name__ == "__main__":
    run_test()
