import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Page Configuration ---
st.set_page_config(page_title="Executive Dashboard", page_icon="📈", layout="wide")
st.title("📈 Executive E-Commerce & AI Assistant Dashboard")

# --- 1. Load Data ---
@st.cache_data
def load_and_clean_data():
    try:
        df = pd.read_csv('dirty_ecommerce_data.csv')
    except FileNotFoundError:
        st.error("Error: 'dirty_ecommerce_data.csv' not found. Please run 'generate_data.py'.")
        st.stop()
        
    initial_rows = len(df)
    df = df.dropna(subset=['Order_Value'])
    df = df[df['Order_Value'] > 0]
    df['Purchase_Date'] = pd.to_datetime(df['Purchase_Date'])
    
    return df, initial_rows

df_raw, initial_rows = load_and_clean_data()

# --- Sidebar Filters ---
st.sidebar.header("⚙️ Data Filters")
countries = ["All"] + list(df_raw['Country'].unique())
selected_country = st.sidebar.selectbox("Select Country", countries)

categories = ["All"] + list(df_raw['Product_Category'].unique())
selected_category = st.sidebar.selectbox("Select Category", categories)

min_date = df_raw['Purchase_Date'].min().date()
max_date = df_raw['Purchase_Date'].max().date()
selected_dates = st.sidebar.date_input("Select Date Range", [min_date, max_date], min_value=min_date, max_value=max_date)

df = df_raw.copy()
if selected_country != "All":
    df = df[df['Country'] == selected_country]
if selected_category != "All":
    df = df[df['Product_Category'] == selected_category]
if len(selected_dates) == 2:
    start_date, end_date = selected_dates
    df = df[(df['Purchase_Date'].dt.date >= start_date) & (df['Purchase_Date'].dt.date <= end_date)]

# --- KPIs ---
total_revenue = df['Order_Value'].sum()
total_transactions = len(df)
unique_customers = df['Customer_ID'].nunique()
avg_order_value = df['Order_Value'].mean() if total_transactions > 0 else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("Filtered Revenue", f"${total_revenue:,.2f}")
col2.metric("Valid Transactions", f"{total_transactions:,}")
col3.metric("Unique Customers", f"{unique_customers:,}")
col4.metric("Avg Order Value", f"${avg_order_value:,.2f}")
st.markdown("---")

# --- MAIN LAYOUT: Dashboard (Left) | AI Agent (Right) ---
# This makes the AI Agent prominently visible 100% of the time on the right side of the screen
col_dash, col_ai = st.columns([7, 3], gap="large")

with col_dash:
    st.subheader("📊 Performance Visuals")
    if total_transactions == 0:
        st.warning("No data available for the selected filters.")
    else:
        # Charts
        c1, c2 = st.columns(2)
        with c1:
            cat_revenue = df.groupby('Product_Category')['Order_Value'].sum().reset_index()
            fig_donut = px.pie(cat_revenue, values='Order_Value', names='Product_Category', hole=0.4)
            st.plotly_chart(fig_donut)
        with c2:
            geo_sales = df.groupby('Country')['Order_Value'].sum().reset_index().sort_values('Order_Value', ascending=False)
            fig_bar = px.bar(geo_sales, x='Country', y='Order_Value', text_auto='.2s', color='Order_Value')
            st.plotly_chart(fig_bar)
            
        st.markdown("---")
        st.subheader("👥 Customer Segments")
        reference_date = df['Purchase_Date'].max() + pd.Timedelta(days=1)
        rfm = df.groupby('Customer_ID').agg({
            'Purchase_Date': lambda x: (reference_date - x.max()).days,
            'Transaction_ID': 'count',
            'Order_Value': 'sum'
        }).reset_index()
        rfm.rename(columns={'Purchase_Date': 'Recency', 'Transaction_ID': 'Frequency', 'Order_Value': 'Monetary'}, inplace=True)
        
        try:
            rfm['R_Score'] = pd.qcut(rfm['Recency'].rank(method='first'), 3, labels=[3, 2, 1])
            rfm['F_Score'] = pd.qcut(rfm['Frequency'].rank(method='first'), 3, labels=[1, 2, 3])
            rfm['M_Score'] = pd.qcut(rfm['Monetary'].rank(method='first'), 3, labels=[1, 2, 3])
            
            def assign_segment(row):
                score = int(row['R_Score']) + int(row['F_Score']) + int(row['M_Score'])
                if score >= 8: return 'VIP Power User'
                elif score >= 5: return 'Regular Active'
                else: return 'At Risk / Churning'
            rfm['Segment'] = rfm.apply(assign_segment, axis=1)
            
            c_seg1, c_seg2 = st.columns([1, 1.5])
            with c_seg1:
                segment_counts = rfm['Segment'].value_counts().reset_index()
                segment_counts.columns = ['Segment', 'Count']
                fig_seg = px.bar(segment_counts, x='Segment', y='Count', color='Segment',
                                 color_discrete_map={'VIP Power User': '#2ca02c', 'Regular Active': '#1f77b4', 'At Risk / Churning': '#d62728'})
                st.plotly_chart(fig_seg)
            with c_seg2:
                st.dataframe(rfm[['Customer_ID', 'Recency', 'Frequency', 'Monetary', 'Segment']], height=350)
        except Exception as e:
            st.error("Not enough data to calculate RFM segments on this view.")

# --- THE PROMINENT AI AGENT ---
with col_ai:
    st.markdown("### 🤖 Executive AI Assistant")
    st.info("I am monitoring the live dashboard. Ask me anything!")
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        st.error("GEMINI_API_KEY missing from .env")
    else:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Chat history
        if "messages" not in st.session_state:
            st.session_state.messages = []
            
        # Display messages inside a scrollable container so it doesn't break the layout
        chat_container = st.container(height=650)
        
        with chat_container:
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
        
        if prompt := st.chat_input("Message the AI Assistant..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with chat_container:
                with st.chat_message("user"):
                    st.markdown(prompt)
                
            summary_stats = f"""
            Active Filters: Country={selected_country}, Category={selected_category}
            Current Metrics: Revenue=${total_revenue:,.2f}, Transactions={total_transactions}, Unique Customers={unique_customers}
            """
            
            ai_prompt = f"Data context: {summary_stats}\nUser: {prompt}\nBe concise, professional, and act as a senior data analyst."
            
            with chat_container:
                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        try:
                            response = model.generate_content(ai_prompt)
                            st.markdown(response.text)
                            st.session_state.messages.append({"role": "assistant", "content": response.text})
                        except Exception as e:
                            st.error(f"Error connecting to AI: {e}")
