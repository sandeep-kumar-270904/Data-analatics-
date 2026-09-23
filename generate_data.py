import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

def generate_enterprise_data():
    np.random.seed(42)
    random.seed(42)
    
    # 1. Customers
    n_customers = 500
    customer_ids = [f"CUST-{1000 + i}" for i in range(n_customers)]
    channels = ['Organic Search', 'Paid Social', 'Referral', 'Direct', 'Email']
    countries = ['USA', 'UK', 'Canada', 'Australia', 'Germany', 'France', 'Japan']
    
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2026, 12, 31)
    date_range = (end_date - start_date).days
    
    customers_df = pd.DataFrame({
        'Customer_ID': customer_ids,
        'Country': [random.choice(countries) for _ in range(n_customers)],
        'Acquisition_Channel': [random.choice(channels) for _ in range(n_customers)],
        'Signup_Date': [start_date + timedelta(days=random.randint(0, date_range)) for _ in range(n_customers)]
    })
    
    # 2. Products
    categories = ['Apparel', 'Electronics', 'Home Decor', 'Footwear', 'Accessories']
    products = []
    for i in range(30):
        cat = random.choice(categories)
        cost = round(random.uniform(5, 300), 2)
        # Price is Cost + Margin (between 20% and 150%)
        margin = random.uniform(0.2, 1.5)
        price = round(cost * (1 + margin), 2)
        products.append({
            'Product_ID': f"PROD-{100 + i}",
            'Category': cat,
            'Unit_Cost': cost,
            'Retail_Price': price
        })
    products_df = pd.DataFrame(products)
    
    # 3. Orders
    n_orders = 5000
    orders = []
    for i in range(n_orders):
        cust = customers_df.sample(1).iloc[0]
        prod = products_df.sample(1).iloc[0]
        
        # Order date must be >= Signup_Date
        cust_signup = cust['Signup_Date']
        max_days = (end_date - cust_signup).days
        if max_days < 1:
            order_date = cust_signup
        else:
            order_date = cust_signup + timedelta(days=random.randint(0, max_days))
            
        quantity = random.choices([1, 2, 3, 4, 5], weights=[60, 20, 10, 5, 5])[0]
        status = random.choices(['Completed', 'Returned', 'Cancelled'], weights=[85, 10, 5])[0]
        
        orders.append({
            'Order_ID': f"ORD-{10000 + i}",
            'Customer_ID': cust['Customer_ID'],
            'Product_ID': prod['Product_ID'],
            'Order_Date': order_date,
            'Quantity': quantity,
            'Status': status
        })
        
    orders_df = pd.DataFrame(orders)
    
    # Sort orders by date
    orders_df = orders_df.sort_values('Order_Date').reset_index(drop=True)
    
    # Save to CSVs
    customers_df.to_csv('customers.csv', index=False)
    products_df.to_csv('products.csv', index=False)
    orders_df.to_csv('orders.csv', index=False)
    
    print("Enterprise Dataset Generated successfully:")
    print(f"- customers.csv ({len(customers_df)} rows)")
    print(f"- products.csv ({len(products_df)} rows)")
    print(f"- orders.csv ({len(orders_df)} rows)")

if __name__ == "__main__":
    generate_enterprise_data()
