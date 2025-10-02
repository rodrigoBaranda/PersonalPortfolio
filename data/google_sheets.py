"""
Google Sheets Data Provider
Handles connection and data retrieval from Google Sheets
"""
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from typing import Dict, Optional
from utils import get_logger


logger = get_logger(__name__)


class GoogleSheetsClient:
    """Client for Google Sheets API interactions"""

    SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

    def __init__(self, credentials_dict: Dict):
        """
        Initialize Google Sheets client

        Args:
            credentials_dict: Service account credentials as dictionary
        """
        self.credentials_dict = credentials_dict
        self._client: Optional[gspread.Client] = None

    @property
    def client(self) -> gspread.Client:
        """Get or create gspread client (lazy loading)"""
        if self._client is None:
            self._client = self._connect()
        return self._client

    def _connect(self) -> Optional[gspread.Client]:
        """
        Establish connection to Google Sheets

        Returns:
            Authorized gspread client or None if connection fails
        """
        try:
            creds = Credentials.from_service_account_info(
                self.credentials_dict,
                scopes=self.SCOPES
            )
            logger.info("Successfully authenticated with Google Sheets")
            return gspread.authorize(creds)
        except Exception as e:
            st.error(f"❌ Error connecting to Google Sheets: {str(e)}")
            logger.exception("Failed to connect to Google Sheets")
            return None

    def get_transactions(self, workbook_name: str, worksheet_name: str) -> Optional[pd.DataFrame]:
        """
        Load transactions from Google Sheets

        Args:
            workbook_name: Name of the Google Sheet workbook
            worksheet_name: Name of the worksheet/tab with transactions

        Returns:
            DataFrame with transaction data or None if loading fails
        """
        try:
            logger.info("Fetching transactions worksheet from '%s'", sheet_name)
            sheet = self.client.open(sheet_name).worksheet("Transactions")
            data = sheet.get_all_records()
            df = pd.DataFrame(data)

            if df.empty:
                st.warning("⚠️ No transactions found in the sheet.")
                logger.warning("Transactions worksheet in '%s' is empty", sheet_name)
                return None

            logger.info("Retrieved %d transactions from Google Sheets", len(df))
            return df
        except gspread.exceptions.SpreadsheetNotFound:
            st.error(f"❌ Google Sheet '{sheet_name}' not found. Please check the name.")
            logger.exception("Spreadsheet '%s' not found", sheet_name)
            return None
        except gspread.exceptions.WorksheetNotFound:
            st.error(f"❌ Worksheet 'Transactions' not found in '{sheet_name}'.")
            logger.exception("Worksheet 'Transactions' missing in '%s'", sheet_name)
            return None
        except Exception as e:
            st.error(f"❌ Error loading transactions: {str(e)}")
            logger.exception("Unexpected error while loading transactions")
            return None
