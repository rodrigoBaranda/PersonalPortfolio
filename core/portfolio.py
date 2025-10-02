"""
Portfolio Management Core Logic
Handles portfolio calculations and data processing
"""
import pandas as pd
from typing import Dict, Optional
from data.google_sheets import GoogleSheetsClient
from data.market_data import MarketDataProvider
from utils import get_logger


logger = get_logger(__name__)


class PortfolioManager:
    """Manages portfolio data and calculations"""

    def __init__(self, credentials_dict: Dict, workbook_name: str, worksheet_name: str):
        """
        Initialize portfolio manager

        Args:
            credentials_dict: Google service account credentials
            workbook_name: Name of the Google Sheet workbook
            worksheet_name: Name of the worksheet/tab containing transactions
        """
        self.sheets_client = GoogleSheetsClient(credentials_dict)
        self.market_data = MarketDataProvider()
        self.workbook_name = workbook_name
        self.worksheet_name = worksheet_name
        self._transactions_df: Optional[pd.DataFrame] = None
        self._positions: Optional[Dict] = None
        logger.info(
            "PortfolioManager created for workbook '%s' and worksheet '%s'",
            workbook_name,
            worksheet_name,
        )

    def load_transactions(self) -> pd.DataFrame:
        """Load transactions from Google Sheets"""
        logger.info(
            "Loading transactions for workbook '%s' / worksheet '%s'",
            self.workbook_name,
            self.worksheet_name,
        )
        self._transactions_df = self.sheets_client.get_transactions(
            self.workbook_name,
            self.worksheet_name,
        )
        if self._transactions_df is None:
            logger.warning(
                "No transactions returned for workbook '%s' / worksheet '%s'",
                self.workbook_name,
                self.worksheet_name,
            )
        else:
            logger.info("Loaded %d transactions", len(self._transactions_df))
        return self._transactions_df

    def get_transactions(self) -> Optional[pd.DataFrame]:
        """Get loaded transactions DataFrame"""
        return self._transactions_df

    def calculate_positions(self) -> Dict:
        """
        Calculate current positions from transactions

        Returns:
            Dictionary mapping ticker to position data
        """
        if self._transactions_df is None or self._transactions_df.empty:
            logger.warning("Cannot calculate positions without transactions")
            return {}

        positions = {}

        for _, row in self._transactions_df.iterrows():
            ticker = self._extract_ticker(row)
            if not ticker:
                logger.debug("Skipping row without ticker: %s", row.to_dict())
                continue

            transaction_type = str(row.get('Type', row.get('type', ''))).upper()
            quantity = float(row.get('Quantity', row.get('quantity', 0)))
            price = float(row.get('Price', row.get('price', 0)))
            currency = row.get('Currency', row.get('currency', 'EUR'))

            if ticker not in positions:
                positions[ticker] = {
                    'quantity': 0,
                    'invested': 0,
                    'currency': currency
                }

            if transaction_type in ['BUY', 'PURCHASE']:
                positions[ticker]['quantity'] += quantity
                positions[ticker]['invested'] += quantity * price
            elif transaction_type == 'SELL':
                positions[ticker]['quantity'] -= quantity
                positions[ticker]['invested'] -= quantity * price
            elif transaction_type == 'DIVIDEND':
                # Dividends reduce cost basis
                positions[ticker]['invested'] -= price
            else:
                logger.debug("Unsupported transaction type '%s' for ticker '%s'", transaction_type, ticker)

        self._positions = positions
        logger.info("Calculated positions for %d tickers", len(positions))
        return positions

    def calculate_portfolio_value(self, manual_values: Dict[str, float]) -> pd.DataFrame:
        """
        Calculate current portfolio value and returns

        Args:
            manual_values: Dictionary of manual price inputs for non-stock positions

        Returns:
            DataFrame with portfolio performance metrics
        """
        if not self._positions:
            logger.warning("No positions available to calculate portfolio value")
            return pd.DataFrame()

        results = []

        for ticker, position in self._positions.items():
            if position['quantity'] <= 0:
                continue

            # Get current price (from market or manual input)
            current_price = self._get_current_price(ticker, manual_values)
            if current_price is None or current_price == 0:
                logger.warning("Skipping ticker '%s' due to missing current price", ticker)
                continue

            # Get exchange rate
            exchange_rate = self.market_data.get_exchange_rate(
                position['currency'],
                'EUR'
            )

            # Calculate values in EUR
            invested_eur = position['invested'] * exchange_rate
            current_value_eur = position['quantity'] * current_price * exchange_rate
            returns = current_value_eur - invested_eur
            returns_pct = (returns / invested_eur * 100) if invested_eur > 0 else 0

            results.append({
                'Ticker': ticker,
                'Quantity': position['quantity'],
                'Currency': position['currency'],
                'Invested (EUR)': round(invested_eur, 2),
                'Current Value (EUR)': round(current_value_eur, 2),
                'Returns (EUR)': round(returns, 2),
                'Returns (%)': round(returns_pct, 2)
            })

        logger.info("Calculated portfolio values for %d positions", len(results))
        return pd.DataFrame(results)

    def get_tickers_needing_manual_input(self) -> list:
        """
        Get list of tickers that need manual price input

        Returns:
            List of ticker symbols that couldn't be fetched from market data
        """
        if not self._positions:
            logger.info("No positions available for manual input check")
            return []

        tickers_needing_input = []

        for ticker, position in self._positions.items():
            if position['quantity'] <= 0:
                continue

            # Try to fetch price
            price = self.market_data.get_stock_price(ticker)
            if price is None:
                tickers_needing_input.append(ticker)
                logger.debug("Ticker '%s' requires manual price input", ticker)

        return tickers_needing_input

    def _extract_ticker(self, row: pd.Series) -> str:
        """Extract ticker from transaction row"""
        return row.get('Ticker', row.get('ticker', row.get('Symbol', '')))

    def _get_current_price(self, ticker: str, manual_values: Dict[str, float]) -> Optional[float]:
        """
        Get current price for a ticker

        Args:
            ticker: Ticker symbol
            manual_values: Dictionary of manual price inputs

        Returns:
            Current price or None if not available
        """
        # Try to get from market data
        price = self.market_data.get_stock_price(ticker)

        # If not available, use manual value
        if price is None:
            price = manual_values.get(ticker, 0.0)
            logger.debug("Using manual price for ticker '%s': %s", ticker, price)

        return price
