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
    render_stock_view,
    render_manual_input_section,
)
from utils import get_logger


logger = get_logger(__name__)


TAB_LABELS = {
    "transactions": "Transactions",
    "summary": "Summary",
    "stocks": "Stock View",
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

    manual_values = dict(st.session_state.get("manual_values", {}))
    portfolio_manager.reset_missing_price_tickers()

    tab_names = [
        TAB_LABELS["transactions"],
        TAB_LABELS["summary"],
        TAB_LABELS["stocks"],
    ]
    transactions_tab, summary_tab, stocks_tab = st.tabs(tab_names)

    with transactions_tab:
        render_transactions_table(transactions_df)

    with summary_tab:
        with st.spinner("🧮 Calculating weighted average costs..."):
            summary_df = portfolio_manager.calculate_weighted_average_cost(
                manual_values=manual_values
            )
        render_weighted_average_cost_summary(summary_df, transactions_df)

    with stocks_tab:
        with st.spinner("📊 Building stock view..."):
            stock_view_df = portfolio_manager.calculate_stock_view(
                manual_values=manual_values
            )
        render_stock_view(stock_view_df)

    missing_tickers = portfolio_manager.get_missing_price_tickers()
    manual_input_candidates = sorted({*missing_tickers, *manual_values.keys()})
    if manual_input_candidates:
        render_manual_input_section(manual_input_candidates)

    # Footer
    st.markdown("---")
    st.caption(f"📅 Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("Dashboard rendering completed")
