import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables
load_dotenv()

st.set_page_config(
    page_title="Nexus Analytics | Enterprise Intelligence",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Executive Styling ---
st.markdown("""
<style>
    /* Metric Card Styling */
    div[data-testid="metric-container"] {
        background: rgba(255, 255, 255, 0.03);
        border-radius: 12px;
        padding: 16px 20px;
        border: 1px solid rgba(128, 128, 128, 0.2);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 18px rgba(0, 0, 0, 0.12);
        border-color: rgba(59, 130, 246, 0.5);
    }
    
    /* Header subtle underline */
    .dashboard-header {
        border-bottom: 1px solid rgba(128, 128, 128, 0.2);
        padding-bottom: 10px;
        margin-bottom: 20px;
    }
    
    /* Quick prompt button style */
    .stButton>button {
        border-radius: 8px;
        font-size: 0.82rem;
        transition: all 0.2s;
    }
</style>
""", unsafe_allow_html=True)

# --- Load & Prep Data ---
@st.cache_data
def load_data():
    try:
        customers = pd.read_csv('customers.csv')
        products = pd.read_csv('products.csv')
        orders = pd.read_csv('orders.csv')
    except Exception:
        # Fallback to generate data if missing
        import generate_data
        generate_data.generate_enterprise_data()
        customers = pd.read_csv('customers.csv')
        products = pd.read_csv('products.csv')
        orders = pd.read_csv('orders.csv')
        
    customers['Signup_Date'] = pd.to_datetime(customers['Signup_Date'])
    orders['Order_Date'] = pd.to_datetime(orders['Order_Date'])
    
    # Relational Join
    df = orders.merge(customers, on='Customer_ID', how='left')
    df = df.merge(products, on='Product_ID', how='left')
    
    # Financial metrics
    df['Revenue'] = df['Quantity'] * df['Retail_Price']
    df['COGS'] = df['Quantity'] * df['Unit_Cost']
    df['Profit'] = df['Revenue'] - df['COGS']
    
    # Valid completed transactions
    df_completed = df[df['Status'] == 'Completed'].copy()
    return df, df_completed

df_raw, df_valid = load_data()

# --- Sidebar Filters ---
with st.sidebar:
    st.title("🔮 Nexus Data Hub")
    st.caption("Enterprise Relational Intelligence")
    st.markdown("---")
    st.subheader("Filter Controls")
    
    all_countries = ["Global"] + sorted(list(df_valid['Country'].dropna().unique()))
    selected_country = st.selectbox("Market Region", all_countries)
    
    all_channels = ["All Channels"] + sorted(list(df_valid['Acquisition_Channel'].dropna().unique()))
    selected_channel = st.selectbox("Acquisition Channel", all_channels)
    
    all_categories = ["All Categories"] + sorted(list(df_valid['Category'].dropna().unique()))
    selected_category = st.selectbox("Product Category", all_categories)
    
    st.markdown("---")
    st.caption("System Status: **Connected to Data Warehouse**")
    st.caption(f"Total Transactions in DB: **{len(df_raw):,}**")

# Apply Filters
df = df_valid.copy()
if selected_country != "Global":
    df = df[df['Country'] == selected_country]
if selected_channel != "All Channels":
    df = df[df['Acquisition_Channel'] == selected_channel]
if selected_category != "All Categories":
    df = df[df['Category'] == selected_category]

# --- Main Dashboard Header ---
st.markdown("""
<div class="dashboard-header">
    <h1 style='margin-bottom: 2px;'>🔮 Nexus Analytics Platform</h1>
    <p style='color: gray; margin: 0;'>Executive E-Commerce Performance, Cohort Retention & AI Intelligence</p>
</div>
""", unsafe_allow_html=True)

# --- Executive KPI Row ---
k1, k2, k3, k4, k5 = st.columns(5)

gross_rev = df['Revenue'].sum()
net_profit = df['Profit'].sum()
margin = (net_profit / gross_rev * 100) if gross_rev > 0 else 0
unique_custs = df['Customer_ID'].nunique()
aov = df['Revenue'].mean() if len(df) > 0 else 0

k1.metric("Gross Revenue", f"${gross_rev:,.0f}", f"{len(df):,} orders")
k2.metric("Net Profit", f"${net_profit:,.0f}", f"{margin:.1f}% margin")
k3.metric("Profit Margin", f"{margin:.1f}%", "EBITDA aligned")
k4.metric("Active Customers", f"{unique_custs:,}", f"${gross_rev/max(1, unique_custs):,.0f} rev/cust")
k5.metric("Avg Order Value", f"${aov:,.2f}", "per checkout")

st.markdown("<br>", unsafe_allow_html=True)

# --- Two Column Grid: [Dashboard 70% | AI Agent 30%] ---
col_dash, col_ai = st.columns([7, 3], gap="large")

with col_dash:
    # Row 1: Profit Margin by Category & Revenue Trend
    r1c1, r1c2 = st.columns(2)
    
    with r1c1:
        st.markdown("##### 📊 Profit Margin & Revenue by Category")
        cat_agg = df.groupby('Category').agg({'Revenue': 'sum', 'Profit': 'sum'}).reset_index()
        cat_agg['Margin_%'] = (cat_agg['Profit'] / cat_agg['Revenue'] * 100).round(1)
        
        fig_cat = px.bar(
            cat_agg, 
            x='Category', 
            y='Profit', 
            color='Margin_%',
            text=cat_agg['Profit'].apply(lambda x: f"${x:,.0f}"),
            color_continuous_scale='Greens',
            hover_data=['Revenue', 'Margin_%']
        )
        fig_cat.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            height=320,
            xaxis_title=None,
            yaxis_title="Net Profit ($)"
        )
        st.plotly_chart(fig_cat, width="stretch")
        
    with r1c2:
        st.markdown("##### 📈 Weekly Revenue & 30-Day Moving Trend")
        weekly = df.set_index('Order_Date').resample('W-MON')['Revenue'].sum().reset_index()
        weekly['30D_MA'] = weekly['Revenue'].rolling(window=4, min_periods=1).mean()
        
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(
            x=weekly['Order_Date'], 
            y=weekly['Revenue'], 
            mode='lines', 
            name='Weekly Actual',
            line=dict(color='#3b82f6', width=2)
        ))
        fig_trend.add_trace(go.Scatter(
            x=weekly['Order_Date'], 
            y=weekly['30D_MA'], 
            mode='lines', 
            name='30-Day Trend',
            line=dict(color='#ef4444', width=2.5, dash='dash')
        ))
        fig_trend.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            height=320,
            hovermode='x unified',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_trend, width="stretch")

    st.markdown("---")
    
    # Row 2: Customer Cohort Retention Heatmap
    st.markdown("##### 🔄 Cohort Retention Matrix (Month-over-Month)")
    st.caption("Percentage of customer cohorts returning to purchase in subsequent months.")
    
    try:
        cohort_df = df.copy()
        cohort_df['CohortMonth'] = cohort_df['Signup_Date'].dt.to_period('M')
        cohort_df['OrderMonth'] = cohort_df['Order_Date'].dt.to_period('M')
        
        cohort_group = cohort_df.groupby(['CohortMonth', 'OrderMonth']).agg(
            n_customers=('Customer_ID', 'nunique')
        ).reset_index()
        cohort_group['PeriodIndex'] = (cohort_group.OrderMonth - cohort_group.CohortMonth).apply(lambda x: x.n)
        
        pivot = cohort_group.pivot_table(index='CohortMonth', columns='PeriodIndex', values='n_customers')
        cohort_sizes = pivot.iloc[:, 0]
        retention_matrix = pivot.divide(cohort_sizes, axis=0)
        
        # Display latest 10 cohorts up to 10 periods
        display_matrix = retention_matrix.iloc[-10:, :10]
        y_labels = [str(p) for p in display_matrix.index]
        x_labels = [f"M+{col}" for col in display_matrix.columns]
        
        fig_heat = px.imshow(
            display_matrix.values,
            labels=dict(x="Months Post Signup", y="Cohort Group", color="Retention"),
            x=x_labels,
            y=y_labels,
            text_auto='.0%',
            color_continuous_scale='Blues',
            aspect="auto"
        )
        fig_heat.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=320)
        st.plotly_chart(fig_heat, width="stretch")
    except Exception as e:
        st.info("Cohort data calculating...")

    st.markdown("---")
    
    # Row 3: RFM Customer Segmentation
    st.markdown("##### 👥 RFM Customer Value Segmentation")
    
    try:
        ref_date = df['Order_Date'].max() + pd.Timedelta(days=1)
        rfm = df.groupby('Customer_ID').agg({
            'Order_Date': lambda x: (ref_date - x.max()).days,
            'Order_ID': 'count',
            'Profit': 'sum'
        }).reset_index()
        rfm.columns = ['Customer_ID', 'Recency', 'Frequency', 'Monetary']
        
        # Scoring
        rfm['R'] = pd.qcut(rfm['Recency'].rank(method='first'), 3, labels=[3, 2, 1])
        rfm['F'] = pd.qcut(rfm['Frequency'].rank(method='first'), 3, labels=[1, 2, 3])
        rfm['M'] = pd.qcut(rfm['Monetary'].rank(method='first'), 3, labels=[1, 2, 3])
        
        def assign_segment(row):
            score = int(row['R']) + int(row['F']) + int(row['M'])
            if score >= 8: return 'Whales (High Value)'
            elif score >= 5: return 'Core Loyalists'
            else: return 'At Risk Churn'
            
        rfm['Segment'] = rfm.apply(assign_segment, axis=1)
        
        r3c1, r3c2 = st.columns([1, 1.4])
        with r3c1:
            seg_dist = rfm['Segment'].value_counts().reset_index()
            fig_rfm = px.pie(
                seg_dist, 
                values='count', 
                names='Segment', 
                hole=0.55,
                color='Segment',
                color_discrete_map={
                    'Whales (High Value)': '#10b981',
                    'Core Loyalists': '#3b82f6',
                    'At Risk Churn': '#f59e0b'
                }
            )
            fig_rfm.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=300)
            st.plotly_chart(fig_rfm, width="stretch")
            
        with r3c2:
            st.caption("Top 25 High-Value Customer Accounts")
            st.dataframe(
                rfm.sort_values('Monetary', ascending=False)[['Customer_ID', 'Segment', 'Monetary', 'Frequency', 'Recency']].head(25),
                height=300,
                width="stretch"
            )
    except Exception as e:
        st.warning("Customer segmentation computing...")


# --- AI Data Scientist Column ---
with col_ai:
    st.markdown("### 🤖 Chief Data Scientist AI")
    st.caption("Powered by Gemini 2.5 with live Python Code Execution")
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        st.error("⚠️ GEMINI_API_KEY is missing from `.env` file.")
    else:
        # Initialize message history
        if "messages" not in st.session_state:
            st.session_state.messages = [
                {
                    "role": "assistant", 
                    "content": "👋 Hello! I am your **Chief Data Scientist AI**. I have live code-execution access to the entire multi-table data warehouse (`customers`, `products`, `orders`). Ask me any complex data or financial question!"
                }
            ]
            
        # Quick prompts
        st.markdown("**💡 Quick Insights:**")
        qp1, qp2 = st.columns(2)
        quick_query = None
        if qp1.button("🏆 Top Profitable Channel", use_container_width=True):
            quick_query = "Which acquisition channel has the highest profit margin and total profit? Give exact figures."
        if qp2.button("🐋 Top 5 Whales", use_container_width=True):
            quick_query = "Who are our top 5 most profitable customers, what countries are they from, and how much did they spend?"
            
        chat_box = st.container(height=580)
        
        with chat_box:
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
                    
        # Check input from chat input or quick prompt button
        user_prompt = st.chat_input("Ask a data question (e.g. Which country generated most revenue?)...")
        if quick_query:
            user_prompt = quick_query
            
        if user_prompt:
            st.session_state.messages.append({"role": "user", "content": user_prompt})
            with chat_box:
                with st.chat_message("user"):
                    st.markdown(user_prompt)
                    
                with st.chat_message("assistant"):
                    with st.spinner("Analyzing data warehouse with Gemini 2.5..."):
                        try:
                            # Python tool function to execute code directly on df_raw
                            def query_dataset(code: str) -> str:
                                """Executes a Python expression or snippet against `df` and returns the output."""
                                try:
                                    local_vars = {"df": df_raw, "pd": pd}
                                    try:
                                        res = eval(code, {}, local_vars)
                                        return str(res)
                                    except SyntaxError:
                                        exec(code, {}, local_vars)
                                        return "Code executed successfully."
                                except Exception as err:
                                    return f"Execution error: {err}"

                            client = genai.Client(api_key=api_key)
                            
                            system_instruction = (
                                "You are an Elite VP of Data Science & BI for an Enterprise E-Commerce Platform. "
                                "You have direct access to `df` containing 5,000 real transactions with columns: "
                                f"{list(df_raw.columns)}. "
                                "When asked a question, ALWAYS use the query_dataset tool to run pandas computations "
                                "and provide exact, verified figures. "
                                "Format your final answer with professional executive Markdown, clear bullet points, "
                                "and strategic business recommendations."
                            )
                            
                            chat = client.chats.create(
                                model="gemini-2.5-flash",
                                config=types.GenerateContentConfig(
                                    tools=[query_dataset],
                                    system_instruction=system_instruction,
                                    temperature=0.2
                                )
                            )
                            
                            response = chat.send_message(user_prompt)
                            ai_output = response.text
                            
                            st.markdown(ai_output)
                            st.session_state.messages.append({"role": "assistant", "content": ai_output})
                        except Exception as e:
                            st.error(f"AI Assistant encountered an issue: {e}")
