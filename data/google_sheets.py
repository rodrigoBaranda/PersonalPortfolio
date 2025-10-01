"""
Google Sheets Data Provider
Handles connection and data retrieval from Google Sheets
"""
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from typing import Dict, Optional

from utils.config import WORKBOOK_NAME, WORKSHEET_NAME


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
            return gspread.authorize(creds)
        except Exception as e:
            st.error(f"❌ Error connecting to Google Sheets: {str(e)}")
            return None

    def get_transactions(self, sheet_name: str = WORKBOOK_NAME) -> Optional[pd.DataFrame]:
        """
        Load transactions from Google Sheets

        Args:
            sheet_name: Name of the Google Sheets workbook. Defaults to the
                configured workbook name.

        Returns:
            DataFrame with transaction data or None if loading fails
        """
        try:
            sheet = self.client.open(sheet_name).worksheet(WORKSHEET_NAME)
            data = sheet.get_all_records()
            df = pd.DataFrame(data)

            if df.empty:
                st.warning("⚠️ No transactions found in the sheet.")
                return None

            return df
        except gspread.exceptions.SpreadsheetNotFound:
            st.error(
                f"❌ Google Sheet workbook '{sheet_name}' not found. "
                "Update the configured workbook name if needed."
            )
            return None
        except gspread.exceptions.WorksheetNotFound:
            st.error(
                f"❌ Worksheet '{WORKSHEET_NAME}' not found in "
                f"'{sheet_name}'. Please ensure the tab name stays exactly "
                f"'{WORKSHEET_NAME}'."
            )
            return None
        except Exception as e:
            st.error(
                f"❌ Error loading transactions from workbook '{sheet_name}' "
                f"/ worksheet '{WORKSHEET_NAME}': {str(e)}"
            )
            return None
