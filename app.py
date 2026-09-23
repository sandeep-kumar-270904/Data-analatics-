import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Page Configuration ---
st.set_page_config(page_title="Executive E-Commerce Dashboard", page_icon="📈", layout="wide")
st.title("📈 Executive E-Commerce Performance & RFM Segmentation Dashboard")

# --- 1. Load and Clean Data ---
@st.cache_data
def load_and_clean_data():
    try:
        df = pd.read_csv('dirty_ecommerce_data.csv')
    except FileNotFoundError:
        st.error("Error: 'dirty_ecommerce_data.csv' not found. Please run 'generate_data.py' locally first.")
        st.stop()
        
    initial_rows = len(df)
    df = df.dropna(subset=['Order_Value'])
    df = df[df['Order_Value'] > 0]
    df['Purchase_Date'] = pd.to_datetime(df['Purchase_Date'])
    
    return df, initial_rows

df_raw, initial_rows = load_and_clean_data()

# --- Sidebar: Filters & AI Configuration ---
st.sidebar.header("⚙️ Dashboard Controls")

# AI Setup: Load key directly from .env without requiring user input
api_key = os.getenv("GEMINI_API_KEY")

if api_key:
    genai.configure(api_key=api_key)
    # Using gemini-1.5-flash which is extremely fast and capable for this
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.sidebar.error("⚠️ GEMINI_API_KEY not found in .env file.")

# Filters
st.sidebar.subheader("🔍 Data Filters")
countries = ["All"] + list(df_raw['Country'].unique())
selected_country = st.sidebar.selectbox("Select Country", countries)

categories = ["All"] + list(df_raw['Product_Category'].unique())
selected_category = st.sidebar.selectbox("Select Category", categories)

min_date = df_raw['Purchase_Date'].min().date()
max_date = df_raw['Purchase_Date'].max().date()
selected_dates = st.sidebar.date_input("Select Date Range", [min_date, max_date], min_value=min_date, max_value=max_date)

# Apply Filters
df = df_raw.copy()
if selected_country != "All":
    df = df[df['Country'] == selected_country]
if selected_category != "All":
    df = df[df['Product_Category'] == selected_category]
if len(selected_dates) == 2:
    start_date, end_date = selected_dates
    df = df[(df['Purchase_Date'].dt.date >= start_date) & (df['Purchase_Date'].dt.date <= end_date)]

st.sidebar.success(f"Showing {len(df)} / {initial_rows} records.")

# --- 2. KPI Metrics Ribbon ---
st.markdown("### 📊 Key Performance Indicators")
col1, col2, col3, col4 = st.columns(4)

total_revenue = df['Order_Value'].sum()
total_transactions = len(df)
unique_customers = df['Customer_ID'].nunique()
avg_order_value = df['Order_Value'].mean() if total_transactions > 0 else 0

col1.metric("Filtered Revenue", f"${total_revenue:,.2f}")
col2.metric("Filtered Transactions", f"{total_transactions:,}")
col3.metric("Unique Customers", f"{unique_customers:,}")
col4.metric("Average Order Value", f"${avg_order_value:,.2f}")

st.markdown("---")

# --- Tabs for layout ---
tab1, tab2, tab3 = st.tabs(["📈 Dashboard Visuals", "👥 RFM Customer Segmentation", "🤖 AI Data Agent"])

# --- Tab 1: Dashboard Visuals ---
with tab1:
    if total_transactions == 0:
        st.warning("No data available for the selected filters.")
    else:
        col_charts1, col_charts2 = st.columns(2)

        with col_charts1:
            st.markdown("#### Category Revenue Share")
            cat_revenue = df.groupby('Product_Category')['Order_Value'].sum().reset_index()
            fig_donut = px.pie(cat_revenue, values='Order_Value', names='Product_Category', hole=0.4, 
                               color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_donut, use_container_width=True)

        with col_charts2:
            st.markdown("#### Global Geographic Sales")
            geo_sales = df.groupby('Country')['Order_Value'].sum().reset_index().sort_values('Order_Value', ascending=False)
            fig_bar = px.bar(geo_sales, x='Country', y='Order_Value', text_auto='.2s', 
                             color='Order_Value', color_continuous_scale='Blues')
            st.plotly_chart(fig_bar, use_container_width=True)
            
        # Add a Trend chart
        st.markdown("#### Revenue Trend Over Time")
        trend_df = df.groupby(df['Purchase_Date'].dt.to_period('M'))['Order_Value'].sum().reset_index()
        trend_df['Purchase_Date'] = trend_df['Purchase_Date'].dt.to_timestamp()
        fig_line = px.line(trend_df, x='Purchase_Date', y='Order_Value', markers=True)
        st.plotly_chart(fig_line, use_container_width=True)

# --- Tab 2: RFM Segmentation ---
with tab2:
    if total_transactions == 0:
        st.warning("No data available for RFM calculation.")
    else:
        reference_date = df['Purchase_Date'].max() + pd.Timedelta(days=1)
        rfm = df.groupby('Customer_ID').agg({
            'Purchase_Date': lambda x: (reference_date - x.max()).days,
            'Transaction_ID': 'count',
            'Order_Value': 'sum'
        }).reset_index()

        rfm.rename(columns={'Purchase_Date': 'Recency', 'Transaction_ID': 'Frequency', 'Order_Value': 'Monetary'}, inplace=True)

        # Apply RFM scoring, gracefully handling low-data situations where quantiles might fail
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

            col_seg1, col_seg2 = st.columns([1, 2])
            with col_seg1:
                st.markdown("#### Segment Distribution")
                segment_counts = rfm['Segment'].value_counts().reset_index()
                segment_counts.columns = ['Segment', 'Count']
                fig_seg = px.bar(segment_counts, x='Segment', y='Count', color='Segment', 
                                 color_discrete_map={'VIP Power User': '#2ca02c', 'Regular Active': '#1f77b4', 'At Risk / Churning': '#d62728'})
                st.plotly_chart(fig_seg, use_container_width=True)

            with col_seg2:
                st.markdown("#### Customer Profiles Database")
                st.dataframe(rfm[['Customer_ID', 'Recency', 'Frequency', 'Monetary', 'Segment']], use_container_width=True, height=400)
        except Exception as e:
            st.error(f"Not enough data diversity to calculate RFM segments on this filtered view.")

# --- Tab 3: AI Data Agent ---
with tab3:
    st.markdown("### 🤖 Chat with your Data")
    st.write("Ask the AI about the current dashboard metrics. It dynamically reads the filtered data you selected in the sidebar.")
    
    if not api_key:
        st.error("⚠️ GEMINI_API_KEY is missing from your .env file.")
    else:
        # Initialize chat history
        if "messages" not in st.session_state:
            st.session_state.messages = []

        # Display chat messages from history
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # React to user input
        if prompt := st.chat_input("Ask a question (e.g., 'What is driving revenue in the top category?'):"):
            
            # 1. Display user message in chat
            st.chat_message("user").markdown(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})

            # 2. Dynamically build context from the CURRENT filtered data state
            summary_stats = f"""
            --- CURRENT DATA CONTEXT ---
            Filters Active: 
            - Country: {selected_country}
            - Category: {selected_category}
            
            Key Metrics:
            - Total Revenue: ${total_revenue:,.2f}
            - Total Transactions: {total_transactions}
            - Unique Customers: {unique_customers}
            - Average Order Value: ${avg_order_value:,.2f}
            
            Category Breakdown:
            {cat_revenue.to_string(index=False) if total_transactions > 0 else 'No data'}
            
            Geographic Breakdown:
            {geo_sales.to_string(index=False) if total_transactions > 0 else 'No data'}
            """
            
            ai_prompt = f"""
            You are a Senior Data Analyst AI embedded in an executive dashboard.
            The user is asking a question based on the currently filtered e-commerce dataset.
            
            Here is the live data summary based on their current filters:
            {summary_stats}
            
            User Question: {prompt}
            
            Provide a highly professional, concise, and insightful answer. If the provided summary doesn't perfectly answer the question, extrapolate the best strategic insight you can based on the metrics available.
            """

            # 3. Get AI response and display it
            with st.chat_message("assistant"):
                with st.spinner("Analyzing live data..."):
                    try:
                        response = model.generate_content(ai_prompt)
                        st.markdown(response.text)
                        st.session_state.messages.append({"role": "assistant", "content": response.text})
                    except Exception as e:
                        st.error(f"Error communicating with Gemini: {e}")
