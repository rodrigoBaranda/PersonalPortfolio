"""
UI Layout Components
Main layout rendering for the Streamlit application
"""
import streamlit as st
from datetime import datetime
from typing import Dict
from core.portfolio import PortfolioManager
from ui.components import (
    render_summary_metrics,
    render_portfolio_table,
    render_manual_input_section,
    render_transactions_expander
)
from utils import get_logger


logger = get_logger(__name__)


def render_sidebar() -> Dict:
    """
    Render sidebar with configuration options

    Returns:
        Dictionary with configuration values
    """
    with st.sidebar:
        st.header("⚙️ Configuration")

        st.subheader("🔐 Google Sheets Credentials")
        credentials_file = st.file_uploader(
            "Upload your Service Account JSON:",
            type=["json"],
            help="Upload the JSON key file downloaded from Google Cloud Console > IAM & Admin > Service Accounts"
        )

        if credentials_file is not None:
            st.caption(f"✅ Loaded credentials file: {credentials_file.name}")
            logger.info("User uploaded credentials file '%s'", credentials_file.name)

        st.subheader("📊 Sheet Configuration")
        sheet_name = st.text_input(
            "Google Sheet Name:",
            value="Transactions",
            help="Name of your Google Sheet (not the tab name)"
        )
        logger.debug("Sheet name input: %s", sheet_name)

        st.markdown("---")
        refresh_button = st.button("🔄 Refresh Data", type="primary", use_container_width=True)
        if refresh_button:
            logger.info("User requested data refresh")

        st.markdown("---")
        st.caption("💡 Your credentials are never stored or shared")

    return {
        'credentials_file': credentials_file,
        'sheet_name': sheet_name,
        'refresh_requested': refresh_button
    }


def render_dashboard(portfolio_manager: PortfolioManager):
    """
    Render main dashboard with portfolio data

    Args:
        portfolio_manager: Initialized PortfolioManager instance
    """
    # Load transactions
    with st.spinner("📥 Loading transactions from Google Sheets..."):
        logger.info("Starting transaction load")
        transactions_df = portfolio_manager.load_transactions()

    if transactions_df is None or transactions_df.empty:
        st.warning("⚠️ No transactions data available. Please check your Google Sheet.")
        logger.warning("No transactions data available after load")
        return

    # Show raw transactions in expander
    render_transactions_expander(transactions_df)

    # Calculate positions
    with st.spinner("🔢 Processing positions..."):
        logger.info("Calculating positions")
        positions = portfolio_manager.calculate_positions()

    if not positions:
        st.warning("⚠️ No active positions found.")
        logger.warning("No active positions found after calculation")
        return

    # Get tickers that need manual input
    tickers_needing_input = portfolio_manager.get_tickers_needing_manual_input()

    # Render manual input section if needed
    if tickers_needing_input:
        logger.info("Tickers requiring manual input: %s", tickers_needing_input)
        render_manual_input_section(tickers_needing_input)

    # Calculate portfolio value with manual inputs
    with st.spinner("📈 Fetching market data..."):
        logger.info("Calculating portfolio value using manual inputs")
        portfolio_df = portfolio_manager.calculate_portfolio_value(
            st.session_state.manual_values
        )

    if portfolio_df.empty:
        st.warning("⚠️ No positions to display. Please provide values for manual inputs.")
        logger.warning("Portfolio data frame is empty after value calculation")
        return

    # Render summary metrics
    render_summary_metrics(portfolio_df)

    st.markdown("---")

    # Render portfolio table
    render_portfolio_table(portfolio_df)

    # Footer
    st.markdown("---")
    st.caption(f"📅 Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("Dashboard rendering completed")
