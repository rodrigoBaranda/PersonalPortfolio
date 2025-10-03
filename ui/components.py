"""
UI Components
Reusable UI components for the Streamlit application
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from typing import List
from utils import get_logger


logger = get_logger(__name__)


def show_setup_instructions():
    """Display setup instructions when credentials are not provided"""
    logger.info("Displaying setup instructions")
    st.info("👈 Add your Google Sheets service account JSON to Streamlit secrets to get started.")

    st.markdown("""
    ### 🚀 Setup Instructions

    #### 1. Create a Google Cloud Project
    - Go to [Google Cloud Console](https://console.cloud.google.com/)
    - Create a new project
    - Enable the **Google Sheets API**

    #### 2. Create Service Account Credentials
    - Navigate to **IAM & Admin** > **Service Accounts**
    - Click **Create Service Account**
    - Give it a name (e.g., "portfolio-tracker")
    - Click **Keys** tab > **Add Key** > **Create New Key**
    - Choose **JSON** format and download

    #### 3. Add Credentials to Streamlit Secrets
    - Open your `.streamlit/secrets.toml`
    - Add a `google_credentials` entry with the JSON content
    - Redeploy or restart the app so the new secrets are available

    #### 4. Share Your Google Sheet
    - Open your Google Sheet named "Transactions"
    - Click **Share** button
    - Add the service account email (from JSON file)
    - Give **Viewer** access

    #### 5. Prepare Your Sheet
    Your "Transactions" sheet should have these columns:
    - **Ticker**: Stock symbol or investment name
    - **Type**: BUY, SELL, or DIVIDEND
    - **Quantity**: Number of shares/units
    - **Price**: Price per share/unit
    - **Currency**: USD, EUR, DKK, CAD, etc.
    - **Date**: Transaction date (optional)
    """)

    with st.expander("📋 Example Sheet Structure"):
        example_data = {
            'Ticker': ['AAPL', 'GOOGL', 'Real Estate #1'],
            'Type': ['BUY', 'BUY', 'BUY'],
            'Quantity': [10, 5, 1],
            'Price': [150.00, 140.00, 50000.00],
            'Currency': ['USD', 'USD', 'EUR'],
            'Date': ['2024-01-15', '2024-02-01', '2023-12-01']
        }
        st.dataframe(pd.DataFrame(example_data), use_container_width=True)
        logger.debug("Rendered example transactions table")


def render_transactions_expander(transactions_df: pd.DataFrame):
    """
    Render expander with raw transactions data

    Args:
        transactions_df: DataFrame with transaction data
    """
    logger.info("Rendering transactions expander with %d rows", len(transactions_df))
    with st.expander("📋 View Raw Transactions"):
        st.dataframe(transactions_df, use_container_width=True)
        st.caption(f"Total transactions: {len(transactions_df)}")


def render_transactions_table(transactions_df: pd.DataFrame):
    """Render the transactions table in the dedicated tab."""
    logger.info("Rendering transactions table with %d rows", len(transactions_df))
    st.subheader("📄 Transactions")
    st.dataframe(transactions_df, use_container_width=True)
    st.caption(f"Total transactions: {len(transactions_df)}")


def render_weighted_average_cost_summary(summary_df: pd.DataFrame):
    """Render portfolio summary by company."""
    st.subheader("📘 Portfolio Overview")

    if summary_df is None or summary_df.empty:
        logger.info("Weighted average cost summary is empty")
        st.info("ℹ️ No transactions available to compute the portfolio overview.")
        return

    formatted_df = summary_df.style.format({
        "Purchased Times": "{:.0f}",
        "Number of Shares": "{:.2f}",
        "Total Invested (EUR)": "€{:,.2f}",
        "Weighted Avg Buy Price (EUR)": "€{:,.2f}",
        "Weighted Avg Sell Price (EUR)": "€{:,.2f}",
        "Current Open Amount EUR": "€{:,.2f}",
    })

    st.dataframe(formatted_df, use_container_width=True)
    st.caption("Summary combines buy and sell transactions and is sorted by current open amount in EUR.")


def render_manual_input_section(tickers: List[str]):
    """
    Render manual input section for non-stock investments

    Args:
        tickers: List of ticker symbols needing manual input
    """
    logger.info("Rendering manual input section for %d tickers", len(tickers))
    st.sidebar.markdown("---")
    st.sidebar.subheader("💼 Manual Value Input")
    st.sidebar.caption("Enter current values for investments without market data:")

    for ticker in tickers:
        current_value = st.session_state.manual_values.get(ticker, 0.0)
        new_value = st.sidebar.number_input(
            f"{ticker}:",
            min_value=0.0,
            value=current_value,
            step=100.0,
            format="%.2f",
            key=f"manual_{ticker}",
            help=f"Current value per unit for {ticker}"
        )
        st.session_state.manual_values[ticker] = new_value
        logger.debug("Manual value set for %s: %s", ticker, new_value)


def render_summary_metrics(portfolio_df: pd.DataFrame):
    """
    Render summary metrics cards

    Args:
        portfolio_df: DataFrame with portfolio performance data
    """
    logger.info("Rendering summary metrics for %d positions", len(portfolio_df))
    total_invested = portfolio_df['Invested (EUR)'].sum()
    total_value = portfolio_df['Current Value (EUR)'].sum()
    total_returns = portfolio_df['Returns (EUR)'].sum()
    total_returns_pct = (total_returns / total_invested * 100) if total_invested > 0 else 0

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "💰 Total Invested",
            f"€{total_invested:,.2f}"
        )

    with col2:
        st.metric(
            "📊 Current Value",
            f"€{total_value:,.2f}"
        )

    with col3:
        st.metric(
            "📈 Total Returns",
            f"€{total_returns:,.2f}",
            f"{total_returns_pct:.2f}%"
        )

    with col4:
        st.metric(
            "📍 Active Positions",
            len(portfolio_df)
        )


def render_portfolio_table(portfolio_df: pd.DataFrame):
    """
    Render portfolio performance table with styling

    Args:
        portfolio_df: DataFrame with portfolio performance data
    """
    logger.info("Rendering portfolio table with %d rows", len(portfolio_df))
    st.subheader("📊 Portfolio Overview")

    # Apply conditional formatting
    def style_returns(val):
        """Color code return values"""
        if isinstance(val, (int, float)):
            if val > 0:
                return 'color: #00b300; font-weight: bold'
            elif val < 0:
                return 'color: #ff4444; font-weight: bold'
        return ''

    styled_df = portfolio_df.style.applymap(
        style_returns,
        subset=['Returns (EUR)', 'Returns (%)']
    ).format({
        'Quantity': '{:.2f}',
        'Invested (EUR)': '€{:,.2f}',
        'Current Value (EUR)': '€{:,.2f}',
        'Returns (EUR)': '€{:,.2f}',
        'Returns (%)': '{:.2f}%'
    })

    st.dataframe(styled_df, use_container_width=True)

    # Download button
    csv = portfolio_df.to_csv(index=False)
    st.download_button(
        label="📥 Download Portfolio Report (CSV)",
        data=csv,
        file_name=f"portfolio_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=False
    )
    logger.debug("Portfolio CSV download ready")
