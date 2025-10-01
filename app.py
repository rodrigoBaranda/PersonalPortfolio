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

    # Determine credentials source
    credentials_dict = None

    if "google_credentials" in st.secrets:
        credentials_dict = dict(st.secrets["google_credentials"])
    else:
        credentials_file = config.get('credentials_file')
        if credentials_file is None:
            show_setup_instructions()
            return

        # Parse credentials from uploaded file
        try:
            credentials_data = credentials_file.getvalue().decode("utf-8")
            credentials_dict = json.loads(credentials_data)
        except UnicodeDecodeError:
            st.error("❌ Unable to read the uploaded file. Please ensure it is a valid JSON file.")
            return
        except json.JSONDecodeError:
            st.error("❌ Invalid JSON format for credentials. Please check and try again.")
            return

    # Initialize portfolio manager
    portfolio_manager = PortfolioManager(
        credentials_dict=credentials_dict,
        workbook_name=config.get('workbook_name')
    )

    # Render dashboard
    render_dashboard(portfolio_manager)


if __name__ == "__main__":
    main()
