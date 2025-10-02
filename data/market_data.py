"""
Market Data Provider
Handles stock prices and currency conversion
"""
import streamlit as st
import yfinance as yf
import requests
from typing import Optional
from utils import get_logger


logger = get_logger(__name__)


class MarketDataProvider:
    """Provider for market data (stocks and currencies)"""

    EXCHANGE_API_URL = "https://api.exchangerate-api.com/v4/latest/"

    @st.cache_data(ttl=3600, show_spinner=False)
    def get_stock_price(_self, ticker: str) -> Optional[float]:
        """
        Fetch current stock price using yfinance

        Args:
            ticker: Stock ticker symbol

        Returns:
            Current price or None if not available
        """
        try:
            logger.debug("Fetching stock price for ticker '%s'", ticker)
            stock = yf.Ticker(ticker)

            # Try to get most recent price from history
            hist = stock.history(period="1d")
            if not hist.empty:
                price = float(hist['Close'].iloc[-1])
                logger.debug("Using historical close price for '%s': %s", ticker, price)
                return price

            # Fallback to info
            info = stock.info
            price = info.get('currentPrice') or info.get('regularMarketPrice')
            if price:
                logger.debug("Using ticker info price for '%s': %s", ticker, price)
            else:
                logger.warning("No price information available for ticker '%s'", ticker)
            return float(price) if price else None

        except Exception:
            # Silently fail - will be handled by manual input
            logger.exception("Failed to fetch stock price for '%s'", ticker)
            return None

    @st.cache_data(ttl=3600, show_spinner=False)
    def get_exchange_rate(_self, from_currency: str, to_currency: str = "EUR") -> float:
        """
        Fetch real-time exchange rate

        Args:
            from_currency: Source currency code
            to_currency: Target currency code (default: EUR)

        Returns:
            Exchange rate (defaults to 1.0 if fetch fails)
        """
        if from_currency == to_currency:
            logger.debug("Exchange rate requested for identical currencies '%s' -> '%s'", from_currency, to_currency)
            return 1.0

        try:
            response = requests.get(
                f"{_self.EXCHANGE_API_URL}{from_currency}",
                timeout=5
            )
            data = response.json()
            rate = float(data['rates'][to_currency])
            logger.debug(
                "Exchange rate fetched for %s -> %s: %s",
                from_currency,
                to_currency,
                rate,
            )
            return rate
        except Exception:
            # Default to 1.0 if exchange rate fetch fails
            logger.exception(
                "Failed to fetch exchange rate from %s to %s; defaulting to 1.0",
                from_currency,
                to_currency,
            )
            return 1.0
