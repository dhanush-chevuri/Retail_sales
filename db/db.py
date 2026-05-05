import mysql.connector
from sqlalchemy import create_engine, text
import os
from utils.logger import setup_logger

logger = setup_logger()

class DatabaseManager:
    def __init__(self, host=None, user=None, password=None, database=None):
        self.host = host or os.getenv('DB_HOST', 'localhost')
        self.user = user or os.getenv('DB_USER', 'root')
        self.password = password or os.getenv('DB_PASSWORD', '')
        self.database = database or os.getenv('DB_NAME', 'retail_db')
        self.engine = None
        
    def get_connection_string(self, include_db=True):
        if include_db:
            return f"mysql+mysqlconnector://{self.user}:{self.password}@{self.host}/{self.database}"
        return f"mysql+mysqlconnector://{self.user}:{self.password}@{self.host}"

    def initialize_db(self):
        try:
            # Connect without database to create it
            conn = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password
            )
            cursor = conn.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.database}")
            conn.close()
            
            # Now initialize engine with database
            self.engine = create_engine(self.get_connection_string())
            self.create_tables()
            logger.info(f"Database {self.database} initialized successfully.")
            return True, "Database initialized."
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            return False, str(e)

    def create_tables(self):
        with self.engine.connect() as conn:
            # 1. Bronze Layer (Raw)
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS bronze_sales (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    order_id VARCHAR(50),
                    order_date VARCHAR(50),
                    store_id VARCHAR(50),
                    product_id VARCHAR(50),
                    product_category VARCHAR(100),
                    quantity_sold VARCHAR(50),
                    unit_price VARCHAR(50),
                    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

            # 2. Silver Layer (Cleaned)
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS silver_sales (
                    order_id VARCHAR(50) PRIMARY KEY,
                    order_date DATETIME,
                    store_id VARCHAR(50),
                    product_id VARCHAR(50),
                    product_category VARCHAR(100),
                    quantity_sold INT,
                    unit_price FLOAT,
                    total_amount FLOAT,
                    order_month INT,
                    order_day INT,
                    transformation_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

            # 3. Gold Layer (Aggregations)
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS gold_sales_by_store (
                    store_id VARCHAR(50) PRIMARY KEY,
                    total_sales FLOAT,
                    total_orders INT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS gold_sales_by_category (
                    product_category VARCHAR(100) PRIMARY KEY,
                    total_sales FLOAT,
                    total_orders INT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS gold_sales_by_date (
                    order_date DATE PRIMARY KEY,
                    total_sales FLOAT,
                    total_orders INT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            logger.info("Tables created successfully.")

    def get_engine(self):
        if not self.engine:
            self.engine = create_engine(self.get_connection_string())
        return self.engine
