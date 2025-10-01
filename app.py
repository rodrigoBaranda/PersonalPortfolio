"""
Investment Portfolio Tracker - Main Application
Entry point for the Streamlit application
"""
import streamlit as st
from ui.layout import render_sidebar, render_dashboard
from ui.components import show_setup_instructions
from core.portfolio import PortfolioManager
from utils.session import init_session_state
import json


def main():
    """Main application entry point"""
    # Initialize session state
    init_session_state()

    # Page configuration
    st.set_page_config(
        page_title="Investment Portfolio Tracker",
        page_icon="📈",
        layout="wide"
    )

    st.title("📈 Investment Portfolio Tracker")
    st.markdown("---")

    # Render sidebar and get configuration
    config = render_sidebar()

    # Check if credentials are provided
    if not config['credentials_json']:
        show_setup_instructions()
        return

    # Parse credentials
    try:
        credentials_dict = json.loads(config['credentials_json'])
    except json.JSONDecodeError:
        st.error("❌ Invalid JSON format for credentials. Please check and try again.")
        return

    # Initialize portfolio manager
    portfolio_manager = PortfolioManager(
        credentials_dict=credentials_dict,
        sheet_name=config['sheet_name']
    )

    # Render dashboard
    render_dashboard(portfolio_manager)


if __name__ == "__main__":
    main()