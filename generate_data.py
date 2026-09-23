import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

def generate_data():
    np.random.seed(42)
    random.seed(42)
    
    n_rows = 1000
    
    # Generate Transaction IDs
    transaction_ids = [f"TXN-{10000 + i}" for i in range(n_rows)]
    
    # Generate Customer IDs (with intentional repeats to allow RFM scoring)
    customer_ids = [f"CUST-{random.randint(100, 350)}" for _ in range(n_rows)]
    
    # Generate Purchase Dates between 2024-01-01 and 2026-12-31
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2026, 12, 31)
    date_range = (end_date - start_date).days
    purchase_dates = [start_date + timedelta(days=random.randint(0, date_range)) for _ in range(n_rows)]
    
    # Generate Product Categories
    categories = ['Apparel', 'Electronics', 'Home Decor', 'Footwear']
    product_categories = [random.choice(categories) for _ in range(n_rows)]
    
    # Generate Countries
    countries = ['USA', 'UK', 'Canada', 'Australia', 'Germany', 'France', 'Japan']
    country_list = [random.choice(countries) for _ in range(n_rows)]
    
    # Generate Order Values (Normal values between $20 and $1500)
    order_values = np.random.uniform(20, 1500, n_rows)
    
    # Inject dirty data: 5% negative values, 10% NaN/null values
    for i in range(n_rows):
        rand_val = random.random()
        if rand_val < 0.05:
            order_values[i] = -abs(order_values[i]) # Negative value
        elif rand_val < 0.15: # 10% chance
            order_values[i] = np.nan # Null value
            
    # Create DataFrame
    df = pd.DataFrame({
        'Transaction_ID': transaction_ids,
        'Customer_ID': customer_ids,
        'Purchase_Date': purchase_dates,
        'Product_Category': product_categories,
        'Order_Value': order_values,
        'Country': country_list
    })
    
    # Save to CSV
    df.to_csv('dirty_ecommerce_data.csv', index=False)
    print("Dataset 'dirty_ecommerce_data.csv' successfully generated with 1000 records.")

if __name__ == "__main__":
    generate_data()
