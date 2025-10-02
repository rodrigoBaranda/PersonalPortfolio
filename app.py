"""
Investment Portfolio Tracker - Main Application
Entry point for the Streamlit application
"""
import json
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
    logger.debug("Sidebar configuration: %s", {k: v for k, v in config.items() if k != 'credentials_file'})

    # Determine credentials source
    credentials_dict = None

    if "google_credentials" in st.secrets:
        credentials_dict = dict(st.secrets["google_credentials"])
        logger.info("Loaded credentials from Streamlit secrets")
    else:
        credentials_file = config.get('credentials_file')
        if credentials_file is None:
            show_setup_instructions()
            logger.warning("Credentials file not provided; showing setup instructions")
            return

        # Parse credentials from uploaded file
        try:
            credentials_data = credentials_file.getvalue().decode("utf-8")
            credentials_dict = json.loads(credentials_data)
            logger.info("Loaded credentials from uploaded file: %s", credentials_file.name)
        except UnicodeDecodeError:
            st.error("❌ Unable to read the uploaded file. Please ensure it is a valid JSON file.")
            logger.exception("Failed to decode uploaded credentials file")
            return
        except json.JSONDecodeError:
            st.error("❌ Invalid JSON format for credentials. Please check and try again.")
            logger.exception("Uploaded credentials file is not valid JSON")
            return

    # Initialize portfolio manager
    portfolio_manager = PortfolioManager(
        credentials_dict=credentials_dict,
        workbook_name=config['workbook_name'],
        worksheet_name=config['worksheet_name']
    )
    logger.info(
        "PortfolioManager initialized for workbook '%s' and worksheet '%s'",
        config['workbook_name'],
        config['worksheet_name']
    )
    logger.info("PortfolioManager initialized for sheet '%s'", config['sheet_name'])

    # Render dashboard
    render_dashboard(portfolio_manager)
    logger.info("Dashboard rendered successfully")


if __name__ == "__main__":
    main()
