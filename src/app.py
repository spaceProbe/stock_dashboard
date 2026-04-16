import streamlit as st
import pandas as pd
import time
from datetime import datetime
import plotly.graph_objects as go
from src.portfolio_manager import PortfolioManager
from src.stock_service import StockService
from src.calculation_engine import CalculationEngine

st.set_page_config(page_title="Stock Value Viewer", layout="wide")

st.title("📈 Stock Value Viewer")
st.write(f"**Current Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Initialize Managers
manager = PortfolioManager("holdings.yaml")
stock_service = StockService()

if "active_chart_ticker" not in st.session_state:
    st.session_state["active_chart_ticker"] = None

def on_table_selection_change(selected_ticker):
    st.session_state["active_chart_ticker"] = selected_ticker

def on_selectbox_change():
    st.session_state["active_chart_ticker"] = st.session_state["chart_ticker_selector"]
st.sidebar.header("Manage Portfolio")

with st.sidebar.expander("Add New Holding"):
    with st.form("add_form", clear_on_submit=True):
        ticker = st.text_input("Ticker (e.g., AAPL)")
        quantity = st.number_input("Quantity", min_value=0.0, step=1.0)
        purchase_price = st.number_input("Purchase Price", min_value=0.0, step=0.01)
        basis_adjustment = st.number_input("Basis Adjustment (e.g., -50 for extra cost)", min_value=-100000000.0, max_value=100000000.0, step=1.0, value=0.0)
        submit_button = st.form_submit_button("Add Holding")

        if submit_button:
            if ticker:
                manager.add_holding(ticker, quantity, purchase_price, basis_adjustment)
                st.success(f"Added {ticker}")
                st.rerun()
            else:
                st.error("Ticker is required")

with st.sidebar.expander("Remove Holding"):
    ticker_to_remove = st.text_input("Enter Ticker to Remove")
    if st.button("Remove"):
        manager.remove_holding(ticker_to_remove)
        st.success(f"Removed {ticker_to_remove}")
        st.rerun()

with st.sidebar.expander("Edit Holding"):
    holdings = manager.load_holdings()
    if holdings:
        tickers = [h['ticker'] for h in holdings]
        selected_ticker = st.selectbox("Select Ticker to Edit", tickers, key="edit_selector")
        
        current_holding = next((h for h in holdings if h['ticker'] == selected_ticker), None)
        
        if current_holding:
            with st.form("edit_form", clear_on_submit=True):
                new_qty = st.number_input("New Quantity", min_value=0.0, value=float(current_holding['quantity']), step=0.1)
                new_price = st.number_input("New Purchase Price", min_value=0.0, value=float(current_holding['purchase_price']), step=0.01)
                new_adj = st.number_input("New Basis Adjustment", min_value=-100000000.0, max_value=100000000.0, value=float(current_holding.get('basis_adjustment', 0.0)), step=1.0)
                
                if st.form_submit_button("Update Holding"):
                    if manager.update_holding(selected_ticker, new_qty, new_price, new_adj):
                        st.success(f"Updated {selected_ticker}")
                        st.rerun()
                    else:
                        st.error("Failed to update holding.")
    else:
        st.info("No holdings available to edit.")

@st.fragment(run_every="10s")
def dashboard_fragment():
    # Main Dashboard
    holdings = manager.load_holdings()

    if not holdings:
        st.info("Your portfolio is empty. Add some stocks using the sidebar!")
        return

    data_list = []
    
    total_market_value = 0.0
    total_net_profit = 0.0
    total_post_tax_value = 0.0

    display_data_list = []

    for holding in holdings:
        ticker = holding['ticker']
        current_price = stock_service.get_current_price(ticker)
        
        if current_price is not None:
            metrics = CalculationEngine.calculate_metrics(holding, current_price)
            
            # Update totals
            total_market_value += metrics['market_value']
            total_net_profit += metrics['net_profit']
            total_post_tax_value += (metrics['market_value'] - metrics['tax_cost'])

            # Add to display list with formatted strings
            display_data_list.append({
                "Ticker": ticker,
                "Quantity": f"{holding['quantity']:,.2f}",
                "Purchase Price": f"${holding['purchase_price']:,.2f}",
                "Current Price": f"${current_price:,.2f}",
                "Market Value": f"${metrics['market_value']:,.2f}",
                "Unrealized P/L": f"${metrics['unrealized_pnl']:,.2f}",
                "Tax Cost": f"${metrics['tax_cost']:,.2f}",
                "Net Profit": f"${metrics['net_profit']:,.2f}"
            })
        else:
            st.error(f"Could not fetch data for {ticker}")

    if display_data_list:
        df = pd.DataFrame(display_data_list)
        event = st.dataframe(
            df, 
            width='stretch', 
            on_select="rerun", 
            selection_mode="single-row"
        )
        
        # Check for selection in the dataframe
        selected_rows = event.selection.rows
        if selected_rows:
            new_ticker = df.iloc[selected_rows[0]]["Ticker"]
            if st.session_state["active_chart_ticker"] != new_ticker:
                st.session_state["active_chart_ticker"] = new_ticker
                st.rerun()
        
        # Summary Stats
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Portfolio Value", f"${total_market_value:,.2f}")
        col2.metric("Total Post-Tax Value", f"${total_post_tax_value:,.2f}")
        col3.metric("Total Net Profit/Loss", f"${total_net_profit:,.2f}", delta=f"{total_net_profit:,.2f}")


        # Historical Charts (Live update version)
        
        if "view_mode" not in st.session_state:
            st.session_state["view_mode"] = "historical"

        col_toggle, col_header = st.columns([0.03, 0.97])
        
        with col_toggle:
            if st.button("⇄", help="Switch View"):
                st.session_state["view_mode"] = (
                    "daily" if st.session_state["view_mode"] == "historical" 
                    else "historical"
                )
                st.rerun()

        with col_header:
            if st.session_state["view_mode"] == "historical":
                st.subheader("Historical Performance")
                chart_mode = st.radio(
                    "View Chart For:",
                    ["Stock Price", "Portfolio Value", "Post-Tax Value", "Profit"],
                    horizontal=True,
                    key="chart_mode_selector"
                )
                if chart_mode == "Stock Price":
                    # Always show the selectbox so the user can always switch back
                    selected_ticker = st.selectbox(
                        "Select Ticker for Chart", 
                        [h['ticker'] for h in holdings], 
                        key="chart_ticker_selector",
                        on_change=on_selectbox_change
                    )

                    # Override with the active chart ticker if it exists and is different from selectbox
                    if st.session_state["active_chart_ticker"] and st.session_state["active_chart_ticker"] != selected_ticker:
                        selected_ticker = st.session_state["active_chart_ticker"]
                        st.info(f"📍 Table Selection active: **{selected_ticker}**")

                    hist_data = stock_service.get_historical_data(selected_ticker)
                    if hist_data is not None:
                        latest_price = stock_service.get_current_price(selected_ticker)
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data['Close'], mode='lines', name='Price', line=dict(color='#00cc96')))
                        if latest_price is not None:
                            fig.add_trace(go.Scatter(x=[hist_data.index[-1]], y=[latest_price], mode='markers', name='Live', marker=dict(color='#ff4b4b', size=12)))
                        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=400, template="plotly_dark", showlegend=False)
                        st.plotly_chart(fig, width="stretch")
                    else:
                        st.warning("No historical data available.")
                elif chart_mode in ["Portfolio Value", "Post-Tax Value", "Profit"]:
                    # Aggregate mode logic
                    all_hist = stock_service.get_all_holdings_history(holdings)
                    if all_hist is not None and not all_hist.empty:
                        agg_series = pd.DataFrame(index=all_hist.index)
                        
                        for h in holdings:
                            ticker = h['ticker']
                            qty = h['quantity']
                            p_price = h['purchase_price']
                            b_adj = h.get('basis_adjustment', 0.0)
                            cost_basis = (qty * p_price) + b_adj
                            
                            if ticker in all_hist.columns:
                                # Market Value
                                agg_series[f'{ticker}_mv'] = all_hist[ticker] * qty
                                # P/L Calculation
                                agg_series[f'{ticker}_pnl'] = agg_series[f'{ticker}_mv'] - cost_basis

                        
                        if not agg_series.empty:
                            portfolio_value = agg_series[[col for col in agg_series.columns if '_mv' in col]].sum(axis=1)
                            profit = agg_series[[col for col in agg_series.columns if '_pnl' in col]].sum(axis=1)
                            
                            fig = go.Figure()
                            if chart_mode == "Portfolio Value":
                                fig.add_trace(go.Scatter(x=agg_series.index, y=portfolio_value, mode='lines', name='Portfolio Value', line=dict(color='#00cc96')))
                            elif chart_mode == "Profit":
                                fig.add_trace(go.Scatter(x=agg_series.index, y=profit, mode='lines', name='Profit', line=dict(color='#ff4b4b')))
                            else:
                                # For Post-Tax Value and Profit, we show Portfolio Value as a fallback or just skip if complex
                                 fig.add_trace(go.Scatter(x=agg_series.index, y=portfolio_value, mode='lines', name='Portfolio Value', line=dict(color='#00cc96')))
                            
                            fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=400, template="plotly_dark", showlegend=False)
                            st.plotly_chart(fig, width="stretch")
                        else:
                            st.warning("No aggregate data available.")
                    else:
                        st.warning("No historical data can be found for aggregation.")
            else:
                # Daily Performance View (Zoomed in from today's open)
                chart_mode_daily = st.radio(
                    "View Chart For:",
                    ["Stock Price", "Portfolio Value", "Post-Tax Value", "Profit"],
                    horizontal=True,
                    key="chart_mode_daily_selector"
                )

                if chart_mode_daily == "Stock Price":
                    # Show individual price lines for each ticker
                    all_hist = stock_service.get_all_holdings_history(holdings, period="1d", interval="5m")
                    if all_hist is not None and not all_hist.empty:
                        fig_daily = go.Figure()
                        for ticker in all_hist.columns:
                            fig_daily.add_trace(go.Scatter(x=all_hist.index, y=all_hist[ticker], mode='lines', name=ticker))
                        fig_daily.update_layout(
                            margin=dict(l=0, r=0, t=30, b=0), 
                            height=400, 
                            template="plotly_dark", 
                            title="Intraday Stock Prices",
                            xaxis_title="Time",
                            yaxis_title="Price ($)"
                        )
                        st.plotly_chart(fig_daily, width="stretch")
                    else:
                        st.warning("No intraday price data available for today.")
                else:
                    # Implement other modes by leveraging the existing logic
                    daily_pnl = stock_service.get_daily_performance(holdings, period="1d", interval="5m")
                    if not daily_pnl.empty:
                        cumulative_pnl = daily_pnl.cumsum()
                        fig_daily = go.Figure(data=[go.Scatter(x=cumulative_pnl.index, y=cumulative_pnl.values, mode='lines', name='Cumulative P/L', line=dict(color='#00cc96'))])
                        fig_daily.update_layout(
                            margin=dict(l=0, r=0, t=30, b=0), 
                            height=400, 
                            template="plotly_dark", 
                            title=f"Intraday {chart_mode_daily} ($)",
                            xaxis_title="Time",
                            yaxis_title="P/L ($)"
                        )
                        st.plotly_chart(fig_daily, width="stretch")
                    else:
                        st.warning("No daily performance data available for today.")





dashboard_fragment()



