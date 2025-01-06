import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(layout="wide")  # Set full-width layout

# Replace with your actual Google Sheets CSV URL
google_sheets_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTuyGRVZuafIk2s7moScIn5PAUcPYEyYIOOYJj54RXYUeugWmOP0iIToljSEMhHrg_Zp8Vab6YvBJDV/pub?output=csv"

@st.cache_data(ttl=0)  # Caching har baar bypass hoga
def load_data(url):
    data = pd.read_csv(url, header=0)
    data.columns = data.columns.str.strip().str.lower()  # Normalize column names

    date_col_candidates = [col for col in data.columns if 'date' in col.lower()]
    if date_col_candidates:
        data['date'] = pd.to_datetime(data[date_col_candidates[0]], errors='coerce')

    numeric_cols = ['nav', 'day change', 'day change %', 'nifty50 value', 'current value', 'nifty50 change %',
                    'dd', 'dd_n50', 'portfolio value', 'absolute gain', 'nifty50']
    for col in numeric_cols:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col].astype(str).str.replace(',', '').str.replace('%', ''), errors='coerce')

    if 'dd' not in data.columns and 'nav' in data.columns:
        data['dd'] = data['nav'] - data['nav'].cummax()

    data.fillna(0, inplace=True)
    return data

# Load data
data = load_data(google_sheets_url)

portfolio_value_raw = data.iloc[0, 0]  # Portfolio value from cell [0,0]
nifty50_value_raw = data.iloc[0, 2]  # Nifty50 value from cell [0,2]
day_change_raw = data.iloc[2, 0]  # Day Change from cell [0,3]
absolute_gain_raw = data.iloc[0, 1]
previous_value_raw = data.iloc[4, 0]

portfolio_value = pd.to_numeric(portfolio_value_raw, errors='coerce')
nifty50_value = pd.to_numeric(nifty50_value_raw, errors='coerce')
day_change = pd.to_numeric(day_change_raw, errors='coerce')
absolute_gain = pd.to_numeric(absolute_gain_raw, errors='coerce')
previous_value = pd.to_numeric(previous_value_raw, errors='coerce')

# Calculate instant day change
day_change = portfolio_value - previous_value
day_change_percent = (day_change / previous_value * 100) if previous_value != 0 else 0

# Total Account Overview Section
st.write("### Total Account Overview", unsafe_allow_html=True)
col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 2])  # 5 equal columns

with col1:
    st.metric("Total Account Value", f"₹{portfolio_value:,.0f}")

with col2:
    st.metric("Absolute Gain", f"₹{absolute_gain:,.0f}")

with col3:
    st.metric("Day Change", f"₹{day_change:,.0f}", f"{day_change_percent:.2f}%")

with col4:
    st.metric("NIFTY50 Benchmark", f"{nifty50_value:,.0f}")

with col5:
    if len(data) > 30:
        month_change = data['current value'].iloc[-1] - data['current value'].iloc[-30]
        month_change_percent = (month_change / data['current value'].iloc[-30] * 100) if \
            data['current value'].iloc[-30] != 0 else 0
        st.metric("Month Change", f"₹{month_change:,.0f}", f"{month_change_percent:.2f}%")
    else:
        st.metric("Month Change", "Insufficient Data")

st.info("Last Update: {}".format(
    datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

# Date Range Selector and Three-Column Layout
col1, col2, col3 = st.columns([1, 4, 1])

with col1:
    st.info("##### Filter by Date Range")
    start_date = st.date_input("Start Date", value=data['date'].min(), key='start_date')
    end_date = st.date_input("End Date", value=data['date'].max(), key='end_date')

# Apply the date filter
filtered_data = data[(data['date'] >= pd.Timestamp(start_date)) & (data['date'] <= pd.Timestamp(end_date))]

if filtered_data.empty:
    st.error("No data available for the selected date range.")
    st.stop()

# Live Charts Section in col2
with col2:
    st.info("##### Model Live Chart")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=filtered_data['date'], y=filtered_data['nav'], mode='lines', name='Strategy',
                             line=dict(color='#244bef', width=1)))
    fig.add_trace(
        go.Scatter(x=filtered_data['date'], y=filtered_data['nifty50 value'], mode='lines', name='Nifty50',
                   line=dict(color='#FB3234', width=1)))
    fig.update_layout(
        height=600,
        plot_bgcolor='#f0f2f6',  # Light grey background
        xaxis=dict(
            showgrid=True,  # Enable grid lines
            gridcolor='white',  # Set grid lines to white
            showline=True,  # Show axis lines
            linecolor='white'  # Axis line color
        ),
        yaxis=dict(
            showgrid=True,  # Enable grid lines
            gridcolor='white',  # Set grid lines to white
            showline=True,  # Show axis lines
            linecolor='white'  # Axis line color
        ),
        legend=dict(
            orientation="h",  # Horizontal orientation
            yanchor="bottom",  # Align to bottom of the legend box
            y=1.02,  # Place above the chart
            xanchor="center",
            x=0.5  # Center the legend horizontally
        )
    )
    st.plotly_chart(fig, use_container_width=True)

    st.info("##### Drawdown Live Chart")
    fig_dd = go.Figure()
    fig_dd.add_trace(go.Scatter(x=filtered_data['date'], y=filtered_data['dd'], mode='lines', name='Strategy Drawdown',
                                line=dict(color='#244bef', width=1)))
    fig_dd.add_trace(
        go.Scatter(x=filtered_data['date'], y=filtered_data['dd_n50'], mode='lines', name='Nifty50 Drawdown',
                   line=dict(color='#FB3234', width=1)))
    fig_dd.update_layout(
        plot_bgcolor='#f0f2f6',
        xaxis=dict(
            showgrid=True,  # Enable grid lines
            gridcolor='white',  # Set grid lines to white
            showline=True,  # Show axis lines
            linecolor='white'  # Axis line color
        ),
        yaxis=dict(
            showgrid=True,  # Enable grid lines
            gridcolor='white',  # Set grid lines to white
            showline=True,  # Show axis lines
            linecolor='white'  # Axis line color
        ),
        legend=dict(
            orientation="h",  # Horizontal orientation
            yanchor="bottom",  # Align to bottom of the legend box
            y=1.02,  # Place above the chart
            xanchor="center",
            x=0.5  # Center the legend horizontally
        )

    )
    st.plotly_chart(fig_dd, use_container_width=True)

# Model Performance Section in col3
with col3:
    st.info("##### Model Performance")
    return_type = st.radio("Select Return Type", ['Inception', 'Yearly', 'Monthly', 'Weekly', 'Daily'], index=1)

    def calculate_performance(return_type):
        latest_value = filtered_data['nav'].iloc[-1]
        if return_type == 'Inception':
            inception_value = filtered_data['nav'].iloc[0]
            return (latest_value - inception_value) / inception_value * 100
        elif return_type == 'Yearly':
            past_date = filtered_data['date'].max() - pd.DateOffset(years=1)
            yearly_data = filtered_data[filtered_data['date'] >= past_date]
            if not yearly_data.empty:
                return (latest_value - yearly_data['nav'].iloc[0]) / yearly_data['nav'].iloc[0] * 100
        elif return_type == 'Monthly':
            past_date = filtered_data['date'].max() - pd.DateOffset(months=1)
            monthly_data = filtered_data[filtered_data['date'] >= past_date]
            if not monthly_data.empty:
                return (latest_value - monthly_data['nav'].iloc[0]) / monthly_data['nav'].iloc[0] * 100
        elif return_type == 'Weekly':
            past_date = filtered_data['date'].max() - pd.DateOffset(weeks=1)
            weekly_data = filtered_data[filtered_data['date'] >= past_date]
            if not weekly_data.empty:
                return (latest_value - weekly_data['nav'].iloc[0]) / weekly_data['nav'].iloc[0] * 100
        elif return_type == 'Daily':
            if len(filtered_data) > 1:
                return (filtered_data['nav'].iloc[-1] - filtered_data['nav'].iloc[-2]) / filtered_data['nav'].iloc[-2] * 100

    performance = calculate_performance(return_type)
    if performance is not None:
        st.write(f"{return_type} Performance: {performance:.2f}%")

# Add performance table
st.info("##### Performance Table")

# Copy the required data and make the date a Datetime object
table_data = filtered_data[['date', 'day change %', 'nifty50 change %']].copy()

# Sort by 'date' in descending order (before formatting)
table_data.sort_values(by='date', ascending=False, inplace=True)

# Format the 'date' column to 'dd-mm-yyyy' format
table_data['date'] = table_data['date'].dt.strftime('%d-%m-%Y')  # Format date
table_data.rename(columns={'day change %': 'strategy', 'nifty50 change %': 'nifty50'}, inplace=True)

# Round values to 2 decimal points (force format as string)
table_data['strategy'] = table_data['strategy'].apply(lambda x: f"{x:.2f}")
table_data['nifty50'] = table_data['nifty50'].apply(lambda x: f"{x:.2f}")

# Apply conditional formatting
def color_positive_negative(val):
    """Style positive values green and negative values light red."""
    color = '#caf1b0' if float(val) > 0 else '#f7e3e5'
    return f'background-color: {color}'

# Display the table with formatting using st.dataframe
styled_table = table_data.style.applymap(color_positive_negative, subset=['strategy', 'nifty50'])

# Show dataframe properly in Streamlit
st.dataframe(styled_table, hide_index=True)
