"""
UI Layout Components
Main layout rendering for the Streamlit application
"""
from datetime import datetime
from typing import Dict

import streamlit as st

from core.portfolio import PortfolioManager
from ui.components import (
    render_transactions_table,
    render_weighted_average_cost_summary,
)
from utils import get_logger


logger = get_logger(__name__)


TAB_LABELS = {
    "transactions": "Transactions",
    "summary": "Summary",
}


def render_sidebar() -> Dict:
    """
    Render a minimal sidebar without interactive controls.

    Returns:
        An empty dictionary (placeholder for future configuration values).
    """
    st.sidebar.empty()

    return {}


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

    tab_names = [TAB_LABELS["transactions"], TAB_LABELS["summary"]]
    transactions_tab, summary_tab = st.tabs(tab_names)

    with transactions_tab:
        render_transactions_table(transactions_df)

    with summary_tab:
        with st.spinner("🧮 Calculating weighted average costs..."):
            summary_df = portfolio_manager.calculate_weighted_average_cost()
        render_weighted_average_cost_summary(summary_df)

    # Footer
    st.markdown("---")
    st.caption(f"📅 Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("Dashboard rendering completed")
