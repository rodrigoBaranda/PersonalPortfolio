"""
Portfolio Management Core Logic
Handles portfolio calculations and data processing
"""
import numpy as np
import pandas as pd
from typing import Dict, Optional

from core.data_quality import clean_transactions
from data.google_sheets import GoogleSheetsClient
from data.market_data import MarketDataProvider
from utils import get_logger


logger = get_logger(__name__)


class PortfolioManager:
    """Manages portfolio data and calculations"""

    def __init__(self, credentials_dict: Dict, spreadsheet_id: str, sheet_name: str):
        """
        Initialize portfolio manager

        Args:
            credentials_dict: Google service account credentials
            spreadsheet_id: Identifier of the Google Spreadsheet
            sheet_name: Name of the worksheet/tab containing transactions
        """
        self.sheets_client = GoogleSheetsClient(credentials_dict)
        self.market_data = MarketDataProvider()
        self.spreadsheet_id = spreadsheet_id
        self.sheet_name = sheet_name
        self._transactions_df: Optional[pd.DataFrame] = None
        self._positions: Optional[Dict] = None
        logger.info(
            "PortfolioManager created for spreadsheet '%s' and sheet '%s'",
            spreadsheet_id,
            sheet_name,
        )

    def load_transactions(self) -> pd.DataFrame:
        """Load transactions from Google Sheets"""
        logger.info(
            "Loading transactions for spreadsheet '%s' / sheet '%s'",
            self.spreadsheet_id,
            self.sheet_name,
        )
        raw_transactions = self.sheets_client.get_transactions(
            self.spreadsheet_id,
            self.sheet_name,
        )
        if raw_transactions is None:
            logger.warning(
                "No transactions returned for spreadsheet '%s' / sheet '%s'",
                self.spreadsheet_id,
                self.sheet_name,
            )
        else:
            logger.info("Loaded %d transactions", len(raw_transactions))

        self._transactions_df = clean_transactions(raw_transactions)
        logger.info("Transactions after data quality checks: %d", len(self._transactions_df))
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
        logger.info("Position calculation not implemented; returning empty result")
        self._positions = {}
        return self._positions

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
        """Resolve the most appropriate price for the given ticker."""
        price = self.market_data.get_stock_price(ticker)
        if price is not None:
            logger.debug("Fetched market price for ticker '%s': %s", ticker, price)
            return price

        if ticker in manual_values:
            manual_price = manual_values[ticker]
            logger.debug("Using manual price for ticker '%s': %s", ticker, manual_price)
            return manual_price

        logger.warning("No price available for ticker '%s'", ticker)
        return None

    @staticmethod
    def _calculate_weighted_average(total_amounts: pd.Series, total_quantities: pd.Series) -> pd.Series:
        """Return weighted average prices, safely handling zero quantities."""
        safe_quantities = total_quantities.replace({0: np.nan})
        return total_amounts.div(safe_quantities)

    def calculate_weighted_average_cost(self) -> pd.DataFrame:
        """Calculate weighted average pricing summary per company including buy and sell data."""
        if self._transactions_df is None or self._transactions_df.empty:
            logger.warning("No transactions loaded before calculating weighted average cost")
            return pd.DataFrame()

        required_columns = {"name", "quantity", "price_per_unit_eur", "gross_amount_eur", "type"}
        missing_columns = required_columns - set(self._transactions_df.columns)

        if missing_columns:
            logger.error(
                "Cannot compute weighted average cost; missing columns: %s",
                ", ".join(sorted(missing_columns)),
            )
            return pd.DataFrame()

        df = self._transactions_df.copy()
        df = df[df["quantity"].notna()]
        df = df[df["quantity"] > 0]

        if df.empty:
            logger.info("No transactions with positive quantity available for summary")
            return pd.DataFrame()

        effective_price = df["price_per_unit_eur"].copy()
        fallback_price = df["gross_amount_eur"] / df["quantity"].replace({0: np.nan})
        effective_price = effective_price.fillna(fallback_price)

        df = df.assign(
            effective_price_eur=effective_price,
            amount_eur=lambda data: data["quantity"] * data["effective_price_eur"],
        )

        def _aggregate_transactions(data: pd.DataFrame, transaction_type: str, prefix: str) -> pd.DataFrame:
            subset = data[data["type"] == transaction_type]
            if subset.empty:
                return pd.DataFrame(
                    columns=[
                        "name",
                        f"{prefix}_quantity",
                        f"{prefix}_amount_eur",
                        f"{prefix}_transactions",
                    ]
                )

            aggregation = subset.groupby("name", dropna=True).agg(
                **{
                    f"{prefix}_quantity": ("quantity", "sum"),
                    f"{prefix}_amount_eur": ("amount_eur", "sum"),
                    f"{prefix}_transactions": ("quantity", "count"),
                }
            )

            return aggregation.reset_index()

        buy_summary = _aggregate_transactions(df, "Buy", "buy")
        sell_summary = _aggregate_transactions(df, "Sell", "sell")

        if buy_summary.empty and sell_summary.empty:
            logger.info("No BUY or SELL transactions available for summary")
            return pd.DataFrame()

        summary = pd.merge(buy_summary, sell_summary, on="name", how="outer")

        numeric_columns = summary.select_dtypes(include=[np.number]).columns
        summary[numeric_columns] = summary[numeric_columns].fillna(0)

        summary["Number of Shares"] = summary["buy_quantity"] - summary["sell_quantity"]
        summary["Total Invested (EUR)"] = summary["buy_amount_eur"]
        summary["Purchased Times"] = summary["buy_transactions"].fillna(0).astype(int)
        summary["Weighted Avg Buy Price (EUR)"] = self._calculate_weighted_average(
            summary["buy_amount_eur"], summary["buy_quantity"]
        )
        summary["Weighted Avg Sell Price (EUR)"] = self._calculate_weighted_average(
            summary["sell_amount_eur"], summary["sell_quantity"]
        )
        summary["Current Open Amount EUR"] = summary["buy_amount_eur"] - summary["sell_amount_eur"]
        summary["Position Status"] = np.where(
            summary["buy_quantity"] > summary["sell_quantity"],
            "Open",
            "Closed",
        )

        summary = summary.rename(columns={"name": "Name"})

        summary = summary.sort_values("Current Open Amount EUR", ascending=False).reset_index(drop=True)

        columns_to_drop = [
            "buy_quantity",
            "sell_quantity",
            "buy_amount_eur",
            "sell_amount_eur",
            "buy_transactions",
            "sell_transactions",
        ]
        summary.drop(columns=[col for col in columns_to_drop if col in summary.columns], inplace=True)

        column_order = [
            "Name",
            "Position Status",
            "Purchased Times",
            "Number of Shares",
            "Total Invested (EUR)",
            "Weighted Avg Buy Price (EUR)",
            "Weighted Avg Sell Price (EUR)",
            "Current Open Amount EUR",
        ]

        return summary[column_order]

