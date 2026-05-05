import pytest
import pandas as pd
import numpy as np
from etl import clean_sales_data



def test_missing_unit_price():
    # Input data with one NaN unit_price
    df = pd.DataFrame({
        'order_id': ['ORD_1', 'ORD_2'],
        'order_date': ['2023-01-01', '2023-01-02'],
        'store_id': ['STR_1', 'STR_1'],
        'product_id': ['P1', 'P2'],
        'product_category': ['A', 'B'],
        'quantity_sold': [1, 2],
        'unit_price': [10.0, np.nan]
    })
    
    cleaned = clean_sales_data(df)
    
    # Assert NaN unit_price row was dropped
    assert len(cleaned) == 1
    assert cleaned.iloc[0]['order_id'] == 'ORD_1'

def test_negative_quantity():
    # Input data with one negative quantity
    df = pd.DataFrame({
        'order_id': ['ORD_1', 'ORD_2'],
        'order_date': ['2023-01-01', '2023-01-02'],
        'store_id': ['STR_1', 'STR_1'],
        'product_id': ['P1', 'P2'],
        'product_category': ['A', 'B'],
        'quantity_sold': [5, -1],
        'unit_price': [10.0, 20.0]
    })
    
    cleaned = clean_sales_data(df)
    
    # Assert negative quantity row was dropped
    assert len(cleaned) == 1
    assert cleaned.iloc[0]['order_id'] == 'ORD_1'

def test_date_format_conversion():
    # Input data with multiple date formats
    df = pd.DataFrame({
        'order_id': ['ORD_1', 'ORD_2'],
        'order_date': ['2023-01-01', '2023-05-15'],
        'store_id': ['STR_1', 'STR_2'],
        'product_id': ['P1', 'P2'],
        'product_category': ['A', 'B'],
        'quantity_sold': [10, 5],
        'unit_price': [10.0, 20.0]
    })
    
    cleaned = clean_sales_data(df)
    
    # Assert both dates were converted to datetime
    assert len(cleaned) == 2
    assert isinstance(cleaned.iloc[0]['order_date'], pd.Timestamp)
    assert cleaned.iloc[0]['order_date'].year == 2023

def test_total_amount_calculation():
    # Input data
    df = pd.DataFrame({
        'order_id': ['ORD_1'],
        'order_date': ['2023-01-01'],
        'store_id': ['STR_1'],
        'product_id': ['P1'],
        'product_category': ['A'],
        'quantity_sold': [5],
        'unit_price': [15.0]
    })
    
    cleaned = clean_sales_data(df)
    
    # Assert total_amount = quantity * price (5 * 15 = 75)
    assert cleaned.iloc[0]['total_amount'] == 75.0
    assert cleaned.iloc[0]['order_month'] == 1
    assert cleaned.iloc[0]['order_day'] == 1
