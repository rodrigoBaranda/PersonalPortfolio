"""Data quality utilities for transaction data."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional

import pandas as pd

from utils import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class DataQualityConfig:
    """Configuration for data quality processing."""

    column_mapping: Dict[str, str]
    numeric_columns: Iterable[str]
    allowed_types: Dict[str, str]
    allowed_currencies: Iterable[str]


DEFAULT_CONFIG = DataQualityConfig(
    # Explicit mapping makes the transformation auditable and easy to share as JSON if needed
    # while still allowing a deterministic snake_case fallback for unexpected headers.
    column_mapping={
        "Ticker": "ticker",
        "Name": "name",
        "Date": "date",
        "ISIN": "isin",
        "Type": "type",
        "Quantity": "quantity",
        "Price per Unit": "price_per_unit",
        "Price per Unit EUR": "price_per_unit_eur",
        "Currency": "currency",
        "Gross Amount": "gross_amount",
        "Gross Amount EUR": "gross_amount_eur",
        "Taxes": "taxes",
        "FX Rate": "fx_rate",
        "Net Base EUR": "net_base_eur",
        "Broker": "broker",
        "Asset Type": "asset_type",
    },
    numeric_columns=(
        "quantity",
        "price_per_unit",
        "price_per_unit_eur",
        "gross_amount",
        "gross_amount_eur",
        "taxes",
        "fx_rate",
        "net_base_eur",
    ),
    allowed_types={
        "BUY": "Buy",
        "SELL": "Sell",
        "DIV": "Dividend",
        "DIVIDEND": "Dividend",
        "DIVIDEND-REINVESTMENT": "Dividend Reinvestment",
        "INTEREST": "Interest",
        "PENSION": "Pension",
    },
    allowed_currencies=("CAD", "DKK", "EUR", "USD", "HKD"),
)


def _to_snake_case(value: str) -> str:
    return (
        value.strip()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("/", "_")
        .lower()
    )


def  clean_transactions(
    transactions: Optional[pd.DataFrame],
    config: DataQualityConfig = DEFAULT_CONFIG,
) -> pd.DataFrame:
    """Clean and standardize the transactions dataframe."""
    if transactions is None or transactions.empty:
        logger.info("No transactions to clean. Returning empty DataFrame.")
        return pd.DataFrame()

    df = transactions.copy()

    # Rename columns using explicit mapping and snake_case fallback
    rename_map = {col: config.column_mapping.get(col, _to_snake_case(col)) for col in df.columns}
    df = df.rename(columns=rename_map)

    # Trim strings and replace empty strings with NA
    object_columns = df.select_dtypes(include=["object", "string"]).columns
    for column in object_columns:
        df[column] = df[column].map(lambda x: x.strip() if isinstance(x, str) else x)
        df[column] = df[column].replace("", pd.NA)

    # Convert numeric columns to floats
    for column in config.numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    # Convert date columns to datetime
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # Normalize transaction types
    if "type" in df.columns:
        df["type"] = df["type"].map(
            lambda x: config.allowed_types.get(str(x).strip().upper(), pd.NA)
            if isinstance(x, str) and x.strip()
            else pd.NA
        )
        before_drop = len(df)
        df = df[df["type"].notna()]
        dropped = before_drop - len(df)
        if dropped:
            logger.debug("Dropped %d transactions with unsupported type", dropped)

    # Normalize currencies and filter allowed ones
    if "currency" in df.columns:
        df["currency"] = df["currency"].map(
            lambda x: str(x).strip().upper() if isinstance(x, str) else x
        )
        before_drop = len(df)
        df = df[df["currency"].isin(config.allowed_currencies)]
        dropped = before_drop - len(df)
        if dropped:
            logger.debug("Dropped %d transactions with unsupported currency", dropped)

    # Filter out rows lacking essential data
    if {"gross_amount", "ticker", "name"}.issubset(df.columns):
        mask = ~(
            (df["gross_amount"].fillna(0) == 0)
            & df["ticker"].isna()
            & df["name"].isna()
        )
        before_drop = len(df)
        df = df[mask]
        dropped = before_drop - len(df)
        if dropped:
            logger.debug("Dropped %d empty placeholder rows", dropped)

    df = df.reset_index(drop=True)
    logger.info("Cleaned transactions: %d rows remaining", len(df))
    return df
