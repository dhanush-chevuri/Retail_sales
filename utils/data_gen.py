import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

def generate_mock_data(n_rows=100):
    """
    Generates messy retail data for testing.
    Columns: order_id, order_date, store_id, product_id, product_category, quantity_sold, unit_price
    """
    categories = ['Electronics', 'Home & Kitchen', 'Beauty', 'Fashion', 'Sports']
    stores = ['STR_001', 'STR_002', 'STR_003', 'STR_004']
    
    data = []
    base_date = datetime.now()
    
    for i in range(n_rows):
        order_id = f"ORD_{1000 + i}"
        if random.random() < 0.2:
            order_date = (base_date - timedelta(days=random.randint(1, 30))).strftime("%m/%d/%Y")
        else:
            order_date = (base_date - timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d")
            
        store_id = random.choice(stores)
        product_id = f"PROD_{random.randint(100, 200)}"
        category = random.choice(categories)
        
        quantity_sold = random.randint(1, 10)
        if random.random() < 0.1:
            quantity_sold = -random.randint(1, 5)
            
        unit_price = round(random.uniform(10, 500), 2)
        if random.random() < 0.05:
            unit_price = round(random.uniform(1000, 5000), 2)
        elif random.random() < 0.1:
            unit_price = np.nan
            
        data.append([order_id, order_date, store_id, product_id, category, quantity_sold, unit_price])
    
    df = pd.DataFrame(data, columns=['order_id', 'order_date', 'store_id', 'product_id', 'product_category', 'quantity_sold', 'unit_price'])
    
    if n_rows > 10:
        df = pd.concat([df, df.iloc[:2]], ignore_index=True)
        
    return df
