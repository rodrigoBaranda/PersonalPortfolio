"""Google Sheets Data Provider.

Handles connection and data retrieval from Google Sheets.
"""
import streamlit as st
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
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
        self._service = None

    @property
    def service(self):
        """Get or create Google Sheets API service (lazy loading)."""
        if self._service is None:
            self._service = self._build_service()
        return self._service

    def _build_service(self):
        """Create the Google Sheets API service client."""
        try:
            if not self.credentials_dict:
                raise ValueError("Google service account credentials were not provided.")
            creds = Credentials.from_service_account_info(
                self.credentials_dict,
                scopes=self.SCOPES
            )
            logger.info("Successfully authenticated with Google Sheets")
            return build('sheets', 'v4', credentials=creds)
        except Exception as e:
            st.error(f"❌ Error connecting to Google Sheets: {str(e)}")
            logger.exception("Failed to connect to Google Sheets")
            return None

    def get_transactions(self, spreadsheet_id: str, sheet_name: str) -> Optional[pd.DataFrame]:
        """
        Load transactions from Google Sheets

        Args:
            spreadsheet_id: ID of the Google Spreadsheet
            sheet_name: Name of the worksheet/tab with transactions (or range reference)

        Returns:
            DataFrame with transaction data or None if loading fails
        """
        try:
            service = self.service
            if service is None:
                raise ConnectionError("Google Sheets service is not available.")

            logger.info(
                "Fetching sheet '%s' from spreadsheet '%s'",
                sheet_name,
                spreadsheet_id,
            )

            result = (
                service.spreadsheets()
                .values()
                .get(spreadsheetId=spreadsheet_id, range=sheet_name)
                .execute()
            )
            values = result.get('values', [])

            if not values:
                st.warning("⚠️ No transactions found in the sheet.")
                logger.warning(
                    "Sheet '%s' in spreadsheet '%s' returned no data",
                    sheet_name,
                    spreadsheet_id,
                )
                return None

            headers, *rows = values
            df = pd.DataFrame(rows, columns=headers)

            logger.info("Retrieved %d transactions from Google Sheets", len(df))
            return df
        except HttpError as error:
            st.error(f"❌ Google Sheets API error: {error}")
            logger.exception(
                "Google Sheets API error for spreadsheet '%s' / sheet '%s'",
                spreadsheet_id,
                sheet_name,
            )
            return None
        except Exception as e:
            st.error(f"❌ Error loading transactions: {str(e)}")
            logger.exception("Unexpected error while loading transactions")
            return None
