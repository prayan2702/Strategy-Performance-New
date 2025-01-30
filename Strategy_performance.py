import streamlit as st
import pandas as pd
import datetime
import yfinance as yf
from datetime import date, timedelta
import plotly.express as px
import plotly.graph_objects as go
import pytz
import locale
import streamlit.components.v1 as components  # Import the components module

#***********************
# Hard-coded credentials
USERNAME = "prayan"
PASSWORD = "prayan"

# Initialize session state for login
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# Login page function
def login():
    st.title("Login")
    
    # Input fields for username and password
    with st.form(key="login_form", clear_on_submit=True):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        # Login button
        submit_button = st.form_submit_button(label="Login")
        if submit_button:
            if username == USERNAME and password == PASSWORD:
                st.session_state.logged_in = True
                st.success("Logged in successfully!")
                st.rerun()  # Reload the app after login
            else:
                st.error("Invalid username or password")

# Main app content function
def app_content():

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
    
    # Helper function to fetch Nifty50 data
    def get_nifty50_data(start_date, end_date):
        """Fetches Nifty50 data from Yahoo Finance."""
        nifty = yf.Ticker("^NSEI")  # Nifty50 ticker symbol
        hist = nifty.history(start=start_date, end=end_date)
        return hist
    
    # Get yesterday's and today's date
    yesterday = date.today() - timedelta(days=1)
    today = date.today()
    
    # Ensure yesterday is not Saturday or Sunday
    if yesterday.weekday() >= 5:
        yesterday -= timedelta(days=yesterday.weekday() - 4)
    
    # Get Nifty50 data for yesterday and today
    nifty_yesterday_data = get_nifty50_data(yesterday, yesterday + timedelta(days=1))
    nifty_today_data = get_nifty50_data(today, today + timedelta(days=1))
    
    # Get current Nifty50 value
    nifty = yf.Ticker("^NSEI")
    nifty_info = nifty.info
    
    # Get yesterday's closing price
    if len(nifty_yesterday_data) >= 1:
        nifty_yesterday = nifty_yesterday_data['Close'].iloc[-1]
    else:
        nifty_yesterday = 0
    
    # Try to get today's closing price
    if len(nifty_today_data) >= 1:
      nifty_today_close = nifty_today_data['Close'].iloc[-1]
    else:
      nifty_today_close = 0
    
    # Try to get current price, with fallbacks
    if "currentPrice" in nifty_info:
        nifty_current = nifty_info["currentPrice"]
    elif "regularMarketPrice" in nifty_info:
        nifty_current = nifty_info["regularMarketPrice"]
    else:
        nifty_current = nifty_today_close  # Fallback to today's close
    
    # If there is no current price, we use the close
    if nifty_current == 0:
      nifty_current = nifty_today_close
    
    # Calculate Nifty50 percentage change
    if nifty_yesterday != 0:
        nifty_change_percent = ((nifty_current - nifty_yesterday) / nifty_yesterday) * 100
    else:
        nifty_change_percent = 0
    
    #******************************************
    
    portfolio_value_raw = data.iloc[0, 0]  # Portfolio value from cell [0,0]
    nifty50_value_raw = data.iloc[0, 2]  # Nifty50 value from cell [0,2]
    day_change_raw = data.iloc[2, 0]  # Day Change from cell [0,3]
    absolute_gain_raw = data.iloc[0, 1]
    previous_value_raw = data.iloc[4, 0]
    xirr_raw = data.iloc[2, 1]  # XIRR value from cell [2,1]
    
    portfolio_value = pd.to_numeric(portfolio_value_raw, errors='coerce')
    nifty50_value = pd.to_numeric(nifty50_value_raw, errors='coerce')
    day_change = pd.to_numeric(day_change_raw, errors='coerce')
    absolute_gain = pd.to_numeric(absolute_gain_raw, errors='coerce')
    previous_value = pd.to_numeric(previous_value_raw, errors='coerce')
    xirr_value = pd.to_numeric(xirr_raw, errors='coerce')
    
    # Calculate instant day change
    day_change = portfolio_value - previous_value
    day_change_percent = (day_change / previous_value * 100) if previous_value != 0 else 0
    
    def format_indian_currency(amount):
        """Formats a number to Indian currency format (lakhs and crores) manually, handling negatives."""
        is_negative = False
        if amount < 0:
            is_negative = True
            amount = abs(amount)  # Work with the absolute value
    
        amount = int(amount)  # Convert to integer
        s = str(amount)
        if len(s) <= 3:
            formatted_value = s
        elif len(s) == 4:
          formatted_value = s[0]+","+s[1:]
        elif len(s) == 5:
          formatted_value = s[:2]+","+s[2:]
        elif len(s) == 6:
            formatted_value = s[:1] + "," + s[1:3] + "," + s[3:]
        elif len(s) == 7:
            formatted_value = s[:2] + "," + s[2:4] + "," + s[4:]
        elif len(s) == 8:
            formatted_value = s[:1] + "," + s[1:3] + "," + s[3:5] + "," + s[5:]
        elif len(s) == 9:
            formatted_value = s[:2] + "," + s[2:4] + "," + s[4:6] + "," + s[6:]
        else:
            formatted_value = "Value too big"
    
        if is_negative:
            return "-" + formatted_value  # Reattach the negative sign
        else:
            return formatted_value
    
    # Try to set locale, but handle potential errors
    try:
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    except locale.Error:
        print("Warning: 'en_US.UTF-8' locale not supported. Number formatting might be incorrect.")
    # Display the Last Update Time
    desired_timezone = pytz.timezone('Asia/Kolkata')  # India Standard Time (IST)
    utc_now = datetime.datetime.now(pytz.utc)
    local_now = utc_now.astimezone(desired_timezone)
    formatted_time = local_now.strftime('%d-%m-%Y %H:%M:%S')
    # st.info for the Last Update
    st.write(f"Last Update: {formatted_time}")
    st.markdown("<br><br>", unsafe_allow_html=True)
    #**********************************
    # Function to fetch portfolio stock list dynamically
    def fetch_stock_list():
        df = pd.read_csv(google_sheets_url)
        if "Portfolio" in df.columns:
            return df["Portfolio"].dropna().tolist()[:30]  # Fetch first 30 stock names
        else:
            st.error("Portfolio column not found in Google Sheet.")
            return []
    
    # Fetch stock list from Google Sheet
    stock_list = fetch_stock_list()
    #******************************
    # Function to fetch portfolio data from Google Sheets
    def fetch_portfolio_data():
        try:
            df = pd.read_csv(google_sheets_url)
            if "Portfolio" in df.columns and "Today Change" in df.columns:
                # Extract and preprocess the data
                df = df[["Portfolio", "Today Change"]].dropna()
                df["Today Change"] = df["Today Change"].str.replace('%', '', regex=False).astype(float)  # Remove '%' and convert to float
                df = df.head(30)  # Limit to the first 30 stocks
                df["Size"] = df["Today Change"].abs()  # Add column for box sizing
                return df
            else:
                st.error("Required columns ('Portfolio', 'Today Change') not found in the Google Sheet.")
                return pd.DataFrame()
        except Exception as e:
            st.error(f"Error fetching data: {e}")
            return pd.DataFrame()
    
    # Fetch data
    portfolio_data = fetch_portfolio_data()
    
    #******************************
    
    
        
    # Total Account Overview Section
    # st.write("### Total Account Overview", unsafe_allow_html=True)
    col1, col2, col3, col4, col5, col6 = st.columns([2, 2, 2, 2, 2, 2])  # 6 equal columns
    
    # Custom CSS to reduce space between markdown and metric components
    st.markdown(
        """
        <style>
            div[data-testid="metric-container"] {
                margin-top: -90px; /* Adjust to reduce space between metric and markdown */
            }
            div[data-testid="stMarkdownContainer"] > p {
                margin-bottom: -90px; /* Tighter gap between markdown text and metric */
            }
            /* Fine-tuning st.info box alignment */
            div.stAlert {
                margin-top: -15px;  /* Pull st.info upwards */
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
    
    # Columns with metrics
    with col1:
        st.markdown("<b style='font-size: 18px;'>Total Account Value</b>", unsafe_allow_html=True)
        st.metric(label="", value=f"₹{format_indian_currency(portfolio_value)}")
    
    with col2:
        st.markdown("<b style='font-size: 18px;'>Absolute Gain</b>", unsafe_allow_html=True)
        st.metric(label="", value=f"₹{format_indian_currency(absolute_gain)}")
    
    with col3:
        st.markdown("<b style='font-size: 18px;'>Day Change</b>", unsafe_allow_html=True)
        st.metric(label="", value=f"₹{format_indian_currency(day_change)}", delta=f"{day_change_percent:.2f}%")
    
    with col4:
        st.markdown("<b style='font-size: 18px;'>NIFTY50 Benchmark</b>", unsafe_allow_html=True)
        st.metric(label="", value=f"{format_indian_currency(nifty_current)}", delta=f"{nifty_change_percent:.2f}%")
    
    with col5:
        st.markdown("<b style='font-size: 18px;'>Current Drawdown</b>", unsafe_allow_html=True)
        if 'dd' in data.columns:  # Ensure 'dd' column exists
            current_drawdown_percent = data['dd'].iloc[-1]  # Get the latest drawdown percentage
            
            if current_drawdown_percent == 0:
                # For 0% drawdown
                st.metric(label="", value="0.00%")
            else:
                # Format with down arrow and red color for negative drawdown
                formatted_percent = f"↓{abs(current_drawdown_percent):.2f}%"  # Ensure arrow and value
                st.metric(label="", value=formatted_percent, delta="", delta_color="inverse")
        else:
            # Handle missing data case
            st.metric(label="", value="Data Unavailable")
    
    with col6:
        st.markdown("<b style='font-size: 18px;'>Strategy XIRR</b>", unsafe_allow_html=True)
        st.metric(label="", value=f"{xirr_value:.2f}%")  # Display XIRR value with 2 decimal points
    
    #**************
    # Extract the required columns for gainers and losers
    top_10_gainers = data.iloc[:, [14, 15, 16]].head(10)  # Columns O, P, Q
    top_10_gainers.columns = ["Symbol", "CMP", "Change%"]
    
    top_10_loosers = data.iloc[:, [18, 19, 20]].head(10)  # Columns S, T, U
    top_10_loosers.columns = ["Symbol", "CMP", "Change%"]
    
    # Ensure "Change%" column is numeric after removing '%'
    top_10_gainers["Change%"] = top_10_gainers["Change%"].str.replace('%', '').astype(float)
    top_10_loosers["Change%"] = top_10_loosers["Change%"].str.replace('%', '').astype(float)
    
    # Define a function to apply color formatting
    def color_grading(val):
        """Color grading for 'Change%' column."""
        if val > 0:
            color = "green"
        elif val < 0:
            color = "red"
        else:
            color = "black"
        return f"color: {color}"
    
    # Apply formatting using Pandas Styler
    styled_gainers = top_10_gainers.style.map(color_grading, subset=["Change%"]).format({"Change%": "{:.2f}%"})
    styled_loosers = top_10_loosers.style.map(color_grading, subset=["Change%"]).format({"Change%": "{:.2f}%"})
    
    # Hide index from the tables
    styled_gainers = styled_gainers.hide(axis='index')
    styled_loosers = styled_loosers.hide(axis='index')
    #***************************
    
    # Date Range Selector and Three-Column Layout
    col1, col2, col3 = st.columns([1, 4, 1])
    
    with col1:
        st.info("##### Date Range")
        start_date = st.date_input("Start Date", value=data['date'].min(), key='start_date')
        end_date = st.date_input("End Date", value=data['date'].max(), key='end_date')
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        
    
        # Add "Top 10 Gainers" table with color grading
        st.info("##### Today's Gainers")
        # Display the table with index hidden
        st.dataframe(styled_gainers, hide_index=True)
    
        # Add "Top 10 Losers" table with color grading
        st.info("##### Today's Losers")
        # Display the table with index hidden
        st.dataframe(styled_loosers, hide_index=True)
        
    # Apply the date filter
    filtered_data = data[(data['date'] >= pd.Timestamp(start_date)) & (data['date'] <= pd.Timestamp(end_date))]
    
    if filtered_data.empty:
        st.error("No data available for the selected date range.")
        st.stop()
    #************************
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
                linecolor='white',  # Axis line color
                tickfont=dict(size=16)  # Increase x-axis font size to 16
            ),
            yaxis=dict(
                showgrid=True,  # Enable grid lines
                gridcolor='white',  # Set grid lines to white
                showline=True,  # Show axis lines
                linecolor='white',  # Axis line color
                tickfont=dict(size=16)  # Increase y-axis font size to 16
            ),
            legend=dict(
                orientation="h",  # Horizontal orientation
                yanchor="bottom",  # Align to bottom of the legend box
                y=1.02,  # Place above the chart
                xanchor="center",
                x=0.5,  # Center the legend horizontally
                font=dict(size=16)  # Increase legend font size to 16
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
                showgrid=True,
                gridcolor='white',
                showline=True,
                linecolor='white',
                tickfont=dict(size=16)  # Increase x-axis font size to 16
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='white',
                showline=True,
                linecolor='white',
                tickfont=dict(size=16)  # Increase y-axis font size to 16
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5,
                font=dict(size=16)  # Increase legend font size to 16
            )
        )
        st.plotly_chart(fig_dd, use_container_width=True)
    
    #**********************
        # # Add Symbol Overview Widget below the charts
        # if stock_list:
        #     st.info("##### Portfolio Symbol Overview")
        
        #     # Generate TradingView Symbol Overview widget code
        #     symbols = [[stock.strip().upper(), f"BSE:{stock.strip().upper()}|1D"] for stock in stock_list]
        
        #     symbol_overview_code = f"""
        #     <!-- TradingView Widget BEGIN -->
        #     <div class="tradingview-widget-container">
        #       <div class="tradingview-widget-container__widget"></div>
        #       <div class="tradingview-widget-copyright"></div>
        #       <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-symbol-overview.js" async>
        #       {{
        #       "symbols": {symbols},
        #       "chartOnly": false,
        #       "width": "100%",
        #       "height": "500",
        #       "locale": "en",
        #       "colorTheme": "light",
        #       "autosize": true,
        #       "showVolume": false,
        #       "showMA": false,
        #       "hideDateRanges": false,
        #       "hideMarketStatus": false,
        #       "hideSymbolLogo": false,
        #       "scalePosition": "right",
        #       "scaleMode": "Normal",
        #       "fontFamily": "-apple-system, BlinkMacSystemFont, Trebuchet MS, Roboto, Ubuntu, sans-serif",
        #       "fontSize": "10",
        #       "noTimeScale": false,
        #       "valuesTracking": "1",
        #       "changeMode": "price-and-percent",
        #       "chartType": "area",
        #       "maLineColor": "#2962FF",
        #       "maLineWidth": 1,
        #       "maLength": 9,
        #       "headerFontSize": "medium",
        #       "lineWidth": 2,
        #       "lineType": 0,
        #       "dateRanges": [
        #         "1d|1",
        #         "1m|30",
        #         "3m|60",
        #         "12m|1D",
        #         "60m|1W",
        #         "all|1M"
        #       ]
        #       }}
        #       </script>
        #     </div>
        #     <!-- TradingView Widget END -->
        #     """.replace("'", '"')  # Replace single quotes with double quotes for JSON compliance
        
        #     # Render the HTML content
        #     components.html(symbol_overview_code, height=500)
        # else:
        #     st.warning("No stocks available for the symbol overview widget.")
    
    #*****************
    
        # Dropdown to select a stock
        if stock_list:
            st.info("##### Portfolio Symbol Overview")
            selected_stock = st.selectbox("",stock_list)
        
            # TradingView widget code
            if selected_stock:
                widget_code = f"""
                <!-- TradingView Widget BEGIN -->
                <div class="tradingview-widget-container" style="width: 100%; max-width: 980px; margin: 0 auto;">
                    <div class="tradingview-widget-container__widget" style="height: 610px; width: 100%;"></div>
                    <div class="tradingview-widget-copyright"></div>
                    <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
                    {{
                        "width": "935",
                        "height": "530",
                        "symbol": "{selected_stock}",
                        "interval": "D",
                        "timezone": "Etc/UTC",
                        "theme": "light",
                        "style": "1",
                        "locale": "en",
                        "allow_symbol_change": true,
                        "calendar": false,
                        "show_popup_button": true,
                        "popup_width": "1000",
                        "popup_height": "650",
                        "hide_volume": true,
                        "support_host": "https://www.tradingview.com"
                    }}
                    </script>
                </div>
                <!-- TradingView Widget END -->
                """
                # Render the widget in Streamlit
                st.components.v1.html(widget_code, height=550)  # Height slightly more for padding
        else:
            st.warning("No stocks available in the portfolio.")
        #**********************************
        # Streamlit App Layout
        st.markdown("<h3 style='text-align: center;'>Heatmap</h3>", unsafe_allow_html=True)
        
        # Custom CSS to set background of Streamlit container to white
        st.markdown("""
            <style>
                .reportview-container .main .block-container {
                    background-color: white;
                }
                .css-1y4v0b4 {
                    background-color: white;
                }
            </style>
        """, unsafe_allow_html=True)
        
        if not portfolio_data.empty:
            # Ensure "Today Change" is treated as a string, remove '%', and convert to numeric
            portfolio_data["Today Change"] = (
                portfolio_data["Today Change"]
                .astype(str)  # Convert to string
                .str.replace('%', '', regex=False)  # Remove '%' sign
                .astype(float)  # Convert to float
            )
        
            # Create a treemap heatmap using Plotly
            fig = px.treemap(
                portfolio_data,
                path=["Portfolio"],  # Stock names as labels
                values="Size",  # Use "Size" column for box sizing
                color="Today Change",  # Use "Today Change" for coloring
                color_continuous_scale=[
                    "#8B0000",  # Dark Red
                    "#FF4500",  # Red-Orange
                    "#FF6347",  # Tomato Red
                    "#F0F0F0",  # Neutral Gray
                    "#90EE90",  # Light Green
                    "#32CD32",  # Lime Green
                    "#006400"   # Dark Green
                ],  # Custom color grading
                range_color=[-5, 5],  # Fix color scale range to include negative values
                custom_data=["Today Change"],  # Pass "Today Change" as custom data
            )
        
            fig.update_traces(
                textinfo="label+text",  # Show stock name and percentage change
                texttemplate="%{label}<br>%{customdata[0]:.2f}%",  # Format text to show label and percentage change
                textfont=dict(color="white"),
                textfont_size=1,  # Increase font size
                insidetextfont=dict(size=30, family="Arial"),  # Adjust inside text font properties
                textposition="middle center",  # Center the text inside the box
            )
        
            fig.update_layout(
                margin=dict(t=0, l=0, r=0, b=50),  # Adjust margins to make space for the color bar
                height=600,  # Fix height to control the chart’s size
                coloraxis_colorbar=dict(
                    title="Change (%)",
                    tickvals=[-5, -3, -2, -1, 0, 1, 2, 3, 5],  # Custom tick values
                    ticktext=["-5%", "-3%", "-2%", "-1%", "0%", "+1%", "+2%", "+3%", "+5%"],  # Custom tick labels
                    orientation="h",  # Horizontal alignment
                    x=0.5,  # Move to bottom center
                    y=-0.1,  # Move below chart
                    len=0.8,  # Length of the color bar
                    thickness=10,  # Thickness of the color bar
                    tickfont=dict(size=12, family="Arial"),  # Match font style
                ),
                # Set background color of the Plotly chart container
                plot_bgcolor="white",  # Background inside the plot area
                paper_bgcolor="white",  # Background outside the plot area
            )
        
            # Display the treemap heatmap
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No data available to display.")
        #********************************
        # Dynamically generate the symbols for the TradingView widget
        symbols = [
            f'{{"proName": "BSE:{stock.strip().upper()}", "title": "{stock.strip().upper()}"}}'
            for stock in stock_list
        ]
        symbols_code = ", ".join(symbols)
        
        # Updated TradingView widget code without the text span
        tradingview_widget = f"""
        <!-- TradingView Widget BEGIN -->
        <div class="tradingview-widget-container">
          <div class="tradingview-widget-container__widget"></div>
          <div class="tradingview-widget-copyright"></div>  <!-- Removed the unnecessary text -->
          <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js" async>
          {{
            "symbols": [
              {symbols_code}
            ],
            "showSymbolLogo": true,
            "isTransparent": false,
            "displayMode": "compact",
            "colorTheme": "light",
            "locale": "en"
          }}
          </script>
        </div>
        <!-- TradingView Widget END -->
        """
        
        # Integrate the widget into Streamlit
        components.html(tradingview_widget, height=85)
    #***********************************
        # Static TradingView widget HTML code for global indices
        widget_html = """
        <!-- TradingView Widget BEGIN -->
        <div class="tradingview-widget-container">
          <div class="tradingview-widget-container__widget"></div>
          <div class="tradingview-widget-copyright"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-tickers.js" async>
          {
          "symbols": [
            {
              "proName": "FOREXCOM:SPXUSD",
              "title": "S&P 500 Index"
            },
            {
              "description": "NASDAQ",
              "proName": "NASDAQ:NDX"
            },
            {
              "description": "Gold",
              "proName": "TVC:GOLD"
            },
            {
              "description": "CRUIDE OIL",
              "proName": "BLACKBULL:BRENT"
            }
          ],
          "isTransparent": false,
          "showSymbolLogo": true,
          "colorTheme": "light",
          "locale": "en"
          }
          </script>
        </div>
        <!-- TradingView Widget END -->
        """
        
        # Embed the widget in your Streamlit app using markdown
        components.html(widget_html, height=200)
    #**********************************************
    
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
            st.markdown("<br><br><br><br>", unsafe_allow_html=True)
        
        # Add performance table
        st.info("##### Performance Table")
        
        # Format the 'date' column to 'dd-mm-yyyy' format
        table_data = filtered_data[['date', 'day change %', 'nifty50 change %']].copy()
        
        # Sort by 'date' in descending order (before formatting)
        table_data.sort_values(by='date', ascending=False, inplace=True)
        
        # Format the 'date' column to 'dd-mm-yyyy' format
        table_data['date'] = table_data['date'].dt.strftime('%d-%m-%Y')  # Format date
        table_data.rename(columns={'date': 'Date','day change %': 'Strategy', 'nifty50 change %': 'Nifty50'}, inplace=True)
        
        # Round values to 2 decimal points (force format as string)
        table_data['Strategy'] = table_data['Strategy'].apply(lambda x: f"{x:.2f}")
        table_data['Nifty50'] = table_data['Nifty50'].apply(lambda x: f"{x:.2f}")
        
        
        # Apply conditional formatting
        def color_positive_negative(val):
            """Style positive values green and negative values light red."""
            color = '#caf1b0' if float(val) > 0 else '#FFD6D7'
            return f'background-color: {color}'
        
        
        # Display the table with formatting using st.dataframe
        styled_table = table_data.style.map(color_positive_negative, subset=['Strategy', 'Nifty50'])
        
        # Show dataframe properly in Streamlit
        st.dataframe(styled_table, hide_index=True)
    # ***************************************************************
if not st.session_state.logged_in:
    login()
else:
    app_content()    

   
