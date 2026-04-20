import streamlit as st
import pandas as pd
import time
from datetime import datetime
import plotly.graph_objects as go
import pytz
from src.portfolio_manager import PortfolioManager
from src.stock_service import StockService
from src.calculation_engine import CalculationEngine

st.set_page_config(page_title="Stock Value Viewer", layout="wide")

def render_performance_chart(df, title, y_axis_label, color="#00cc96", mode="lines", show_legend=False):
    """Reusable function to render all performance charts."""
    if df is None or df.empty:
        st.warning("No data available for this chart.")
        return

    fig = go.Figure()
    
    # Identify columns to plot. If 'Close' is present, it's the primary metric.
    cols_to_plot = []
    if 'Close' in df.columns:
        cols_to_plot = ['Close']
    else:
        cols_to_plot = df.columns

    if mode == "lines":
        for col in cols_to_plot:
            # Use the provided color for single-column charts, otherwise use a default palette or trace colors
            trace_color = color if len(df.columns) <= 1 else None
            fig.add_trace(go.Scatter(
                x=df.index, 
                y=df[col], 
                mode='lines', 
                name=col, 
                line=dict(color=trace_color) if trace_color else None
            ))
    elif mode == "bars":
        fig.add_trace(go.Bar(x=df.index, y=df.iloc[:, 0], name=df.columns[0], marker_color=color))

    fig.update_layout(
        title=title,
        xaxis_title="Date/Time",
        yaxis_title=y_axis_label,
        margin=dict(l=0, r=0, t=30, b=0),
        height=400,
        template="plotly_dark",
        showlegend=show_legend
    )
    st.plotly_chart(fig, use_container_width=True)

st.write(f"**Current Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

manager = PortfolioManager("holdings.yaml")
stock_service = StockService()

if "active_chart_ticker" not in st.session_state:
    st.session_state["active_chart_ticker"] = None

def on_selectbox_change():
    st.session_state["active_chart_ticker"] = st.session_state["chart_ticker_selector"]

st.sidebar.header("Manage Portfolio")

with st.sidebar.expander("Add New Holding"):
    with st.form("add_form", clear_on_submit=True):
        ticker = st.text_input("Ticker (e.g., AAPL)")
        quantity = st.number_input("Quantity", min_value=0.0, step=1.0)
        purchase_price = st.number_input("Purchase Price", min_value=0.0, step=0.01)
        basis_adjustment = st.number_input("Basis Adjustment", min_value=-100000000.0, max_value=100000000.0, step=1.0, value=0.0)
        if st.form_submit_button("Add Holding") and ticker:
            manager.add_holding(ticker, quantity, purchase_price, basis_adjustment)
            st.success(f"Added {ticker}")
            st.rerun()

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

@st.fragment(run_every="10s")
def dashboard_fragment():
    holdings = manager.load_holdings()
    if not holdings:
        st.info("Your portfolio is empty.")
        return

    data_list = []
    total_mv, total_profit, total_post_tax = 0.0, 0.0, 0.0
    display_list = []

    for h in holdings:
        ticker = h['ticker']
        price = stock_service.get_current_price(ticker)
        if price is not None:
            m = CalculationEngine.calculate_metrics(h, price)
            total_mv += m['market_value']
            total_profit += m['net_profit']
            total_post_tax += (m['market_value'] - m['tax_cost'])
            display_list.append({
                "Ticker": ticker, "Qty": f"{h['quantity']:,.2f}", 
                "Price": f"${price:,.2f}", "MV": f"${m['market_value']:,.2f}",
                "P/L": f"${m['unrealized_pnl']:,.2f}", "Net Profit": f"${m['net_profit']:,.2f}"
            })

    if display_list:
        df_display = pd.DataFrame(display_list)
        event = st.dataframe(df_display, on_select="rerun", selection_mode="single-row")
        if event.selection.rows:
            st.session_state["active_chart_ticker"] = df_display.iloc[event.selection.rows[0]]["Ticker"]

        col1, col2, col3 = st.columns(3)
        col1.metric("Portfolio Value", f"${total_mv:,.2f}")
        col2.metric("Post-Tax Value", f"${total_post_tax:,.2f}")
        col3.metric("Total Net Profit", f"${total_profit:,.2f}", delta=f"{total_profit:,.2f}")

        st.divider()
        
        if "view_mode" not in st.session_state: st.session_state["view_mode"] = "historical"
        
        col_t, col_h = st.columns([0.05, 0.95])
        with col_t:
            if st.button("⇄"):
                st.session_state["view_mode"] = "daily" if st.session_state["view_mode"] == "historical" else "historical"
                st.rerun()

        with col_h:
            if st.session_state["view_mode"] == "historical":
                st.subheader("Historical Performance")
                mode = st.radio("View Chart For:", ["Stock Price", "Portfolio Value", "Post-Tax Value", "Profit"], horizontal=True, key="hist_mode")
                
                if mode == "Stock Price":
                    all_t = ["All Stocks"] + [h['ticker'] for h in holdings]
                    sel = st.selectbox("Select Ticker", all_t, key="chart_ticker_selector", on_change=on_selectbox_change)
                    if sel == "All Stocks":
                        hist = stock_service.get_all_holdings_history(holdings)
                        render_performance_chart(hist, "All Stocks Performance", "Price ($)", show_legend=True)
                    else:
                        # Check active selection override
                        if st.session_state["active_chart_ticker"] and st.session_state["active_chart_ticker"] != sel:
                            sel = st.session_state["active_chart_ticker"]
                        hist = stock_service.get_historical_pattern(sel, period="1mo")
                        render_performance_chart(hist, f"{sel} Price", "Price ($)")
                else:
                    all_h = stock_service.get_all_holdings_history(holdings)
                    if not all_h.empty:
                        agg = pd.DataFrame(index=all_h.index)
                        for h in holdings:
                            t, q = h['ticker'], h['quantity']
                            if t in all_h.columns:
                                agg[f"{t}_mv"] = all_h[t] * q
                                agg[f"{t}_pnl"] = (all_h[t] * q) - ((q * h['purchase_price']) + h.get('basis_adjustment', 0))
                        
                        if mode == "Portfolio Value":
                            v = agg[[c for c in agg.columns if '_mv' in c]].sum(axis=1)
                            render_performance_chart(pd.DataFrame({'Value': v}, index=v.index), "Total Portfolio Value", "USD ($)")
                        elif mode == "Profit":
                            p = agg[[c for c in agg.columns if '_pnl' in c]].sum(axis=1)
                            render_performance_chart(pd.DataFrame({'Profit': p}, index=p.index), "Total Profit/Loss", "USD ($)", color="#ff4b4b")
                        else: # Post-Tax (Approximation)
                            v = agg[[c for c in agg.columns if '_mv' in c]].sum(axis=1)
                            render_performance_chart(pd.DataFrame({'Post-Tax': v}, index=v.index), "Total Post-Tax Value", "USD ($)")
            else:
                st.subheader("Daily Performance")
                view_type = st.radio("View Chart For:", ["Stock Price", "Intraday P/L"], horizontal=True, key="daily_view_mode")
                target = st.selectbox("Select Ticker (Intraday)", ["All Stocks"] + [h['ticker'] for h in holdings], key="daily_sel")
                h_list = holdings if target == "All Stocks" else [h for h in holdings if h['ticker'] == target]
                
                if view_type == "Stock Price":
                    if target == "All Stocks":
                        hist = stock_service.get_all_holdings_history(holdings, period="1d", interval="5m")
                        if not hist.empty:
                            render_performance_chart(hist, "Intradray Prices", "Price ($)", show_legend=True)
                        else:
                            st.warning("No intraday price data.")
                    else:
                        hist = stock_service.get_historical_pattern(target, period="1d", interval="5m")
                        if hist is not None and not hist.empty:
                            render_performance_chart(hist, f"{target} Price", "Price ($)", color="#00cc96")
                        else:
                            st.warning("No intraday price data.")
                else: # Intraday P/L
                    perf = stock_service.get_daily_performance(h_list, period="1d", interval="5m")
                    if not perf.empty:
                        render_performance_chart(pd.DataFrame({'P/L': perf}, index=perf.index), f"Intraday P/L ({target})", "USD ($)", color="#ff4b4b")
                    else:
                        st.warning("No intraday P/L data.")

dashboard_fragment()