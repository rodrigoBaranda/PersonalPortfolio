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

        refresh_button = st.button("🔄 Refresh Data", type="primary", use_container_width=True)
        if refresh_button:
            logger.info("User requested data refresh")

        st.markdown("---")
        st.caption("💡 Google Sheets credentials are loaded from Streamlit secrets")

    return {
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
