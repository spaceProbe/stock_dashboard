import yfinance as yf
import streamlit as st
import pandas as pd
from datetime import datetime, time

class StockService:
    @staticmethod
    def get_historical_data(ticker, period="1mo", interval="1d"):
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period=period, interval=interval)
            if hist.empty:
                return None
            return hist
        except Exception:
            return None

    @staticmethod
    def get_historical_pattern(ticker, period="1d", interval="5m"):
        """Alias for compatibility with app.py call."""
        return StockService.get_historical_data(ticker, period, interval)

    @staticmethod
    def get_current_price(ticker):
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1d")
            if not hist.empty:
                return hist['Close'].iloc[-1]
            return None
        except Exception:
            return None

    @staticmethod
    def get_all_holdings_history(holdings, period="1mo", interval="1d"):
        """Fetches and aligns historical data for all holdings in the portfolio."""
        if not holdings:
            return pd.DataFrame()

        all_series = []
        for h in holdings:
            ticker = h['ticker']
            hist = StockService.get_historical_data(ticker, period, interval)
            if hist is not None and not hist.empty:
                # We only need the 'Close' price for calculation
                series = hist['Close'].rename(ticker)
                all_series.append(series)
        
        if not all_series:
            return pd.DataFrame()

        # Merge all series on date index
        combined_df = pd.concat(all_series, axis=1).ffill().bfill()
        return combined_df

    @staticmethod
    def get_daily_performance(holdings, period="1d", interval="5m"):
        """Calculates the intraday P/L for the entire portfolio."""
        if not holdings:
            return pd.Series(dtype=float)

        all_hist = StockService.get_all_holdings_history(holdings, period, interval)
        if all_hist.empty:
            return pd.Series(dtype=float)

        daily_pnl = pd.Series(0.0, index=all_hist.index)
        
        for h in holdings:
            ticker = h['ticker']
            qty = h['quantity']
            if ticker in all_hist.columns:
                # price change * qty
                price_change = all_hist[ticker].diff()
                daily_pnl += price_change * qty
        
        return daily_pnl


