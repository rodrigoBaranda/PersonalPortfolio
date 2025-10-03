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

    def _prepare_transaction_summary(self) -> pd.DataFrame:
        """Aggregate buy and sell data per security."""
        if self._transactions_df is None or self._transactions_df.empty:
            logger.warning("No transactions loaded before preparing transaction summary")
            return pd.DataFrame()

        required_columns = {
            "name",
            "quantity",
            "price_per_unit_eur",
            "gross_amount_eur",
            "type",
        }
        missing_columns = required_columns - set(self._transactions_df.columns)

        if missing_columns:
            logger.error(
                "Cannot prepare transaction summary; missing columns: %s",
                ", ".join(sorted(missing_columns)),
            )
            return pd.DataFrame()

        df = self._transactions_df.copy()
        df = df[df["name"].notna()]
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

        def _first_valid(series: pd.Series) -> Optional[str]:
            valid = series.dropna()
            return valid.iloc[0] if not valid.empty else None

        metadata = (
            df.groupby("name", dropna=True)
            .agg(
                ticker=("ticker", _first_valid),
                currency=("currency", _first_valid),
            )
            .reset_index()
        )

        def _aggregate_transactions(
            data: pd.DataFrame, transaction_type: str, prefix: str
        ) -> pd.DataFrame:
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

        summary = metadata
        if not buy_summary.empty:
            summary = summary.merge(buy_summary, on="name", how="left")
        else:
            summary = summary.assign(
                buy_quantity=0.0,
                buy_amount_eur=0.0,
                buy_transactions=0,
            )

        if not sell_summary.empty:
            summary = summary.merge(sell_summary, on="name", how="left")
        else:
            summary = summary.assign(
                sell_quantity=0.0,
                sell_amount_eur=0.0,
                sell_transactions=0,
            )

        for column in [
            "buy_quantity",
            "buy_amount_eur",
            "buy_transactions",
            "sell_quantity",
            "sell_amount_eur",
            "sell_transactions",
        ]:
            if column in summary.columns:
                summary[column] = summary[column].fillna(0.0)

        summary["buy_transactions"] = summary["buy_transactions"].astype(int)
        summary["sell_transactions"] = summary["sell_transactions"].astype(int)

        summary = summary.assign(
            total_invested_eur=summary["buy_amount_eur"],
            shares_outstanding=summary["buy_quantity"] - summary["sell_quantity"],
            weighted_avg_buy_price_eur=self._calculate_weighted_average(
                summary["buy_amount_eur"], summary["buy_quantity"]
            ),
            weighted_avg_sell_price_eur=self._calculate_weighted_average(
                summary["sell_amount_eur"], summary["sell_quantity"]
            ),
        )

        return summary

    def calculate_weighted_average_cost(self) -> pd.DataFrame:
        """Calculate weighted average pricing summary per company including buy and sell data."""
        summary = self._prepare_transaction_summary()
        if summary.empty:
            return pd.DataFrame()

        rng = np.random.default_rng()
        base_buy_price = summary["weighted_avg_buy_price_eur"]
        variation = rng.uniform(0.9, 1.1, size=len(summary))
        simulated_current_value = base_buy_price * variation
        simulated_current_value = simulated_current_value.round(2)
        simulated_current_value[base_buy_price.isna()] = np.nan
        summary["current_value"] = simulated_current_value
        summary["Current Open Amount EUR"] = (
            summary["buy_amount_eur"] - summary["sell_amount_eur"]
        ).clip(lower=0)
        summary["Position Status"] = np.where(
            summary["shares_outstanding"] > 0,
            "Open",
            "Closed",
        )

        summary = summary.rename(
            columns={
                "name": "Name",
                "buy_transactions": "Purchased Times",
                "shares_outstanding": "Number of Shares",
                "total_invested_eur": "Total Invested (EUR)",
                "weighted_avg_buy_price_eur": "Weighted Avg Buy Price (EUR)",
                "weighted_avg_sell_price_eur": "Weighted Avg Sell Price (EUR)",
            }
        )

        if "Purchased Times" in summary.columns:
            summary["Purchased Times"] = summary["Purchased Times"].astype(int)

        summary = summary.sort_values("Current Open Amount EUR", ascending=False).reset_index(drop=True)

        columns_to_drop = [
            "ticker",
            "currency",
            "sell_transactions",
            "buy_quantity",
            "sell_quantity",
            "buy_amount_eur",
            "sell_amount_eur",
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
            "current_value",
            "Current Open Amount EUR",
        ]

        return summary[column_order]

    def calculate_stock_view(self, manual_values: Optional[Dict[str, float]] = None) -> pd.DataFrame:
        """Return a stock-centric view with profit calculations."""
        manual_values = manual_values or {}
        summary = self._prepare_transaction_summary()
        if summary.empty:
            return pd.DataFrame()

        results = []

        for _, row in summary.iterrows():
            name = row.get("name")
            ticker = row.get("ticker")
            currency = row.get("currency") or "EUR"
            buy_qty = float(row.get("buy_quantity", 0.0))
            sell_qty = float(row.get("sell_quantity", 0.0))
            invested_eur = float(row.get("total_invested_eur", 0.0))
            avg_buy = row.get("weighted_avg_buy_price_eur")
            avg_sell = row.get("weighted_avg_sell_price_eur")

            remaining_qty = max(buy_qty - sell_qty, 0.0)
            realized_value_eur = float(row.get("sell_amount_eur", 0.0))

            current_price_eur = np.nan
            unrealized_value_eur = np.nan

            if remaining_qty > 0 and ticker:
                market_price = self._get_current_price(ticker, manual_values)
                if market_price is not None:
                    exchange_rate = self.market_data.get_exchange_rate(currency, "EUR")
                    current_price_eur = float(market_price) * exchange_rate
                    unrealized_value_eur = remaining_qty * current_price_eur
                else:
                    logger.debug(
                        "Skipping current price for '%s' due to missing market data", ticker
                    )
            elif remaining_qty <= 0:
                unrealized_value_eur = 0.0

            if np.isnan(unrealized_value_eur) and remaining_qty <= 0:
                # Closed positions with no market price simply have no unrealized component
                unrealized_value_eur = 0.0

            total_value_eur = realized_value_eur
            if not pd.isna(unrealized_value_eur):
                total_value_eur += unrealized_value_eur
            elif remaining_qty > 0:
                total_value_eur = np.nan

            profit_eur = np.nan
            profit_pct = np.nan
            if invested_eur > 0 and not pd.isna(total_value_eur):
                profit_eur = total_value_eur - invested_eur
                profit_pct = (profit_eur / invested_eur) * 100

            if remaining_qty > 0 and sell_qty > 0:
                position_status = "Partially Closed"
            elif remaining_qty > 0:
                position_status = "Open"
            else:
                position_status = "Closed"

            def _round_or_nan(value: Optional[float]) -> float:
                if value is None or pd.isna(value):
                    return np.nan
                return round(float(value), 2)

            results.append(
                {
                    "Name": name,
                    "Weighted Avg Buy Price (EUR)": _round_or_nan(avg_buy),
                    "Weighted Avg Sell Price (EUR)": _round_or_nan(avg_sell),
                    "Current Price (EUR)": _round_or_nan(current_price_eur),
                    "Profit (%)": _round_or_nan(profit_pct),
                    "Profit (EUR)": _round_or_nan(profit_eur),
                    "Realized Value (EUR)": _round_or_nan(realized_value_eur),
                    "Unrealized Value (EUR)": _round_or_nan(unrealized_value_eur),
                    "Total Value (EUR)": _round_or_nan(total_value_eur),
                    "Shares Outstanding": _round_or_nan(remaining_qty),
                    "Position Status": position_status,
                }
            )

        stock_view_df = pd.DataFrame(results)
        stock_view_df = stock_view_df.sort_values("Name").reset_index(drop=True)
        return stock_view_df

