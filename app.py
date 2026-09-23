import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load env
load_dotenv()

st.set_page_config(page_title="Nexus Analytics", page_icon="🔮", layout="wide")

# --- Custom CSS ---
st.markdown("""
<style>
    /* KPI Cards */
    div[data-testid="metric-container"] {
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        border: 1px solid rgba(128, 128, 128, 0.2);
    }
    div[data-testid="metric-container"]:hover {
        box-shadow: 0 6px 12px rgba(0,0,0,0.2);
        transform: translateY(-2px);
        transition: all 0.3s ease;
    }
</style>
""", unsafe_allow_html=True)

st.title("🔮 Nexus Analytics Platform")
st.markdown("Enterprise Data Warehouse & AI Intelligence")

# --- Load Data ---
@st.cache_data
def load_data():
    try:
        customers = pd.read_csv('customers.csv')
        products = pd.read_csv('products.csv')
        orders = pd.read_csv('orders.csv')
    except Exception as e:
        st.error("Data missing. Please run `python generate_data.py`.")
        st.stop()
        
    # Convert dates
    customers['Signup_Date'] = pd.to_datetime(customers['Signup_Date'])
    orders['Order_Date'] = pd.to_datetime(orders['Order_Date'])
    
    # Merge data
    df = orders.merge(customers, on='Customer_ID', how='left')
    df = df.merge(products, on='Product_ID', how='left')
    
    # Calculate financial metrics
    df['Revenue'] = df['Quantity'] * df['Retail_Price']
    df['COGS'] = df['Quantity'] * df['Unit_Cost']
    df['Profit'] = df['Revenue'] - df['COGS']
    
    # Exclude returned/cancelled from active revenue
    df_valid = df[df['Status'] == 'Completed']
    return df, df_valid

df_raw, df_valid = load_data()

# --- Sidebar Filters ---
st.sidebar.header("🎛️ Global Filters")
selected_country = st.sidebar.selectbox("Market (Country)", ["Global"] + list(df_valid['Country'].unique()))
selected_channel = st.sidebar.selectbox("Acquisition Channel", ["All Channels"] + list(df_valid['Acquisition_Channel'].unique()))

df = df_valid.copy()
if selected_country != "Global":
    df = df[df['Country'] == selected_country]
if selected_channel != "All Channels":
    df = df[df['Acquisition_Channel'] == selected_channel]

# --- KPIs ---
st.markdown("### 📈 Key Performance Indicators")
col1, col2, col3, col4 = st.columns(4)

total_rev = df['Revenue'].sum()
total_profit = df['Profit'].sum()
margin = (total_profit / total_rev) * 100 if total_rev > 0 else 0
active_customers = df['Customer_ID'].nunique()

col1.metric("Gross Revenue", f"${total_rev:,.0f}")
col2.metric("Net Profit", f"${total_profit:,.0f}")
col3.metric("Profit Margin", f"{margin:.1f}%")
col4.metric("Active Customers", f"{active_customers:,}")

st.markdown("<br>", unsafe_allow_html=True)

# --- Layout: Main | AI Agent ---
col_main, col_ai = st.columns([7, 3], gap="large")

with col_main:
    # TABS FOR ADVANCED ANALYTICS
    t1, t2, t3 = st.tabs(["💰 Profitability & Sales", "🔄 Cohort Retention", "👥 RFM Customer Segments"])
    
    with t1:
        st.markdown("#### Profit Margin by Category")
        cat_profit = df.groupby('Category').agg({'Revenue': 'sum', 'Profit': 'sum'}).reset_index()
        cat_profit['Margin'] = cat_profit['Profit'] / cat_profit['Revenue']
        fig_profit = px.bar(cat_profit, x='Category', y='Profit', color='Margin', 
                            color_continuous_scale='Greens', text_auto='.2s',
                            title="Net Profit Contribution by Category")
        
        st.plotly_chart(fig_profit, use_container_width=True)
        
        st.markdown("#### Revenue Trend Forecast")
        # Simple moving average forecast
        trend = df.groupby(df['Order_Date'].dt.to_period('W'))['Revenue'].sum().reset_index()
        trend['Order_Date'] = trend['Order_Date'].dt.to_timestamp()
        trend['30-Day Moving Avg'] = trend['Revenue'].rolling(window=4).mean()
        
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(x=trend['Order_Date'], y=trend['Revenue'], mode='lines', name='Actual Revenue', line=dict(color='#3b82f6')))
        fig_trend.add_trace(go.Scatter(x=trend['Order_Date'], y=trend['30-Day Moving Avg'], mode='lines', name='Trend', line=dict(color='#ef4444', dash='dash')))
        fig_trend.update_layout(hovermode='x unified')
        st.plotly_chart(fig_trend, use_container_width=True)

    with t2:
        st.markdown("#### Customer Retention Heatmap")
        st.info("Tracks the percentage of customers who return to make purchases in subsequent months.")
        
        # Cohort calculation
        df['CohortMonth'] = df['Signup_Date'].dt.to_period('M')
        df['OrderMonth'] = df['Order_Date'].dt.to_period('M')
        
        df_cohort = df.groupby(['CohortMonth', 'OrderMonth']).agg(n_customers=('Customer_ID', 'nunique')).reset_index()
        df_cohort['PeriodNumber'] = (df_cohort.OrderMonth - df_cohort.CohortMonth).apply(lambda x: x.n)
        
        cohort_pivot = df_cohort.pivot_table(index='CohortMonth', columns='PeriodNumber', values='n_customers')
        cohort_size = cohort_pivot.iloc[:, 0]
        retention = cohort_pivot.divide(cohort_size, axis=0)
        
        # Plotly Heatmap
        # Limit to first 12 periods for visualization
        retention_vis = retention.iloc[-12:, :12]
        
        y_labels = [str(p) for p in retention_vis.index]
        x_labels = [f"M+{i}" for i in retention_vis.columns]
        
        fig_heatmap = px.imshow(
            retention_vis.values,
            labels=dict(x="Months Since Signup", y="Cohort Month", color="Retention"),
            x=x_labels,
            y=y_labels,
            text_auto='.0%',
            color_continuous_scale='Blues',
            aspect="auto"
        )

        st.plotly_chart(fig_heatmap, use_container_width=True)

    with t3:
        st.markdown("#### Actionable Customer Segmentation")
        reference_date = df['Order_Date'].max() + pd.Timedelta(days=1)
        rfm = df.groupby('Customer_ID').agg({
            'Order_Date': lambda x: (reference_date - x.max()).days,
            'Order_ID': 'count',
            'Profit': 'sum'
        }).reset_index()
        rfm.columns = ['Customer_ID', 'Recency', 'Frequency', 'Monetary']
        
        try:
            rfm['R'] = pd.qcut(rfm['Recency'].rank(method='first'), 3, labels=[3, 2, 1])
            rfm['F'] = pd.qcut(rfm['Frequency'].rank(method='first'), 3, labels=[1, 2, 3])
            rfm['M'] = pd.qcut(rfm['Monetary'].rank(method='first'), 3, labels=[1, 2, 3])
            
            def seg(row):
                score = int(row['R']) + int(row['F']) + int(row['M'])
                if score >= 8: return 'Whales (High Value)'
                elif score >= 5: return 'Core Loyalists'
                else: return 'At Risk Churn'
            rfm['Segment'] = rfm.apply(seg, axis=1)
            
            c_s1, c_s2 = st.columns([1, 1])
            with c_s1:
                seg_counts = rfm['Segment'].value_counts().reset_index()
                fig_seg = px.pie(seg_counts, values='count', names='Segment', hole=0.5, 
                                 color_discrete_sequence=['#10b981', '#3b82f6', '#ef4444'])
                st.plotly_chart(fig_seg, use_container_width=True)
            with c_s2:
                st.dataframe(rfm.sort_values('Monetary', ascending=False).head(50), height=350, use_container_width=True)
        except Exception as e:
            st.error("Insufficient data for RFM quantiles.")


with col_ai:
    st.markdown("### 🤖 Advanced Data Scientist AI")
    st.info("I have direct code execution access to the entire multi-table data warehouse (Customers, Products, Orders). Ask me complex questions!")
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        st.error("GEMINI_API_KEY missing from .env")
    else:
        if "messages" not in st.session_state:
            st.session_state.messages = []
            
        chat_container = st.container(height=650)
        
        with chat_container:
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
        
        if prompt := st.chat_input("E.g., Which acquisition channel brought the highest LTV customers?"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with chat_container:
                with st.chat_message("user"):
                    st.markdown(prompt)
                
            with chat_container:
                with st.chat_message("assistant"):
                    with st.spinner("Writing Python code to analyze raw data..."):
                        try:
                            from langchain_experimental.agents import create_pandas_dataframe_agent
                            from langchain_google_genai import ChatGoogleGenerativeAI
                            
                            # Using gemini-1.5-pro for complex coding
                            llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", google_api_key=api_key, temperature=0)
                            
                            # Give agent access to the FULL RAW DATAFRAME
                            agent = create_pandas_dataframe_agent(
                                llm, 
                                df_raw, 
                                verbose=False, 
                                allow_dangerous_code=True
                            )
                            
                            response = agent.invoke(prompt)
                            output = str(response.get("output", response))
                            
                            st.markdown(output)
                            st.session_state.messages.append({"role": "assistant", "content": output})
                        except Exception as e:
                            st.error(f"Error executing advanced data analysis: {e}")
