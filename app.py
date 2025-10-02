"""
Investment Portfolio Tracker - Main Application
Entry point for the Streamlit application
"""
import streamlit as st
from ui.layout import render_sidebar, render_dashboard
from ui.components import show_setup_instructions
from core.portfolio import PortfolioManager
from utils.session import init_session_state
from utils import get_logger


logger = get_logger(__name__)


def main():
    """Main application entry point"""
    # Initialize session state
    init_session_state()
    logger.info("Initialized session state")

    # Page configuration
    st.set_page_config(
        page_title="Investment Portfolio Tracker",
        page_icon="📈",
        layout="wide"
    )
    logger.info("Page configuration set")

    st.title("📈 Investment Portfolio Tracker")
    st.markdown("---")

    # Render sidebar and get configuration
    config = render_sidebar()
    logger.debug("Sidebar configuration: %s", config)

    # Determine credentials source
    credentials_dict = None

    if "google_credentials" in st.secrets:
        credentials_dict = dict(st.secrets["google_credentials"])
        logger.info("Loaded credentials from Streamlit secrets")
    else:
        show_setup_instructions()
        logger.warning("Google Sheets credentials not found in Streamlit secrets")
        return

    # Determine sheet configuration (kept out of the sidebar)
    secrets_sheets = st.secrets.get("google_sheets", {})
    spreadsheet_id = (
        st.secrets.get("google_spreadsheet_id")
        or st.secrets.get("google_sheets_spreadsheet_id")
        or secrets_sheets.get("spreadsheet_id")
    )
    sheet_name = (
        st.secrets.get("google_sheet_name")
        or st.secrets.get("google_sheets_sheet_name")
        or secrets_sheets.get("sheet_name", "Transactions")
    )

    if not spreadsheet_id:
        st.error(
            "❌ Google Spreadsheet ID not configured. Please add `google_spreadsheet_id` to your Streamlit secrets."
        )
        logger.error("Spreadsheet ID not configured in Streamlit secrets")
        return

    # Initialize portfolio manager
    portfolio_manager = PortfolioManager(
        credentials_dict=credentials_dict,
        spreadsheet_id=spreadsheet_id,
        sheet_name=sheet_name,
    )
    logger.info(
        "PortfolioManager initialized for spreadsheet '%s' and sheet '%s'",
        spreadsheet_id,
        sheet_name,
    )

    # Render dashboard
    render_dashboard(portfolio_manager)
    logger.info("Dashboard rendered successfully")


if __name__ == "__main__":
    main()
