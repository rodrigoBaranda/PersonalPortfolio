"""
UI Components
Reusable UI components for the Streamlit application
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from typing import List, Tuple
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


def render_weighted_average_cost_summary(
    summary_df: pd.DataFrame, transactions_df: pd.DataFrame
):
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
        "current_value": "€{:,.2f}",
        "Current Open Amount EUR": "€{:,.2f}",
    })

    st.dataframe(formatted_df, use_container_width=True)
    st.caption("Summary combines buy and sell transactions and is sorted by current open amount in EUR.")

    if transactions_df is None or transactions_df.empty:
        logger.info("Skipping monthly charts because transactions data is unavailable")
        st.info("ℹ️ Add dated transactions to explore income and contribution trends.")
        return

    if "date" not in transactions_df.columns or transactions_df["date"].isna().all():
        logger.info("Skipping monthly charts because transaction dates are missing")
        st.info("ℹ️ Add dates to your transactions to unlock monthly charts.")
        return

    transactions_with_dates = transactions_df[transactions_df["date"].notna()].copy()
    transactions_with_dates["date"] = pd.to_datetime(transactions_with_dates["date"])

    def prepare_monthly_series(df: pd.DataFrame, transaction_type: str) -> pd.DataFrame:
        subset = df[df["type"] == transaction_type].copy()
        if subset.empty:
            return pd.DataFrame(columns=["Month", "Amount"])

        if "gross_amount_eur" not in subset.columns:
            logger.info("Missing gross_amount_eur column for %s chart", transaction_type)
            return pd.DataFrame(columns=["Month", "Amount"])

        subset = subset[subset["gross_amount_eur"].notna()]
        if subset.empty:
            return pd.DataFrame(columns=["Month", "Amount"])

        subset["Month"] = subset["date"].dt.to_period("M").dt.to_timestamp()
        monthly = (
            subset.groupby("Month")["gross_amount_eur"].sum().reset_index(name="Amount")
        )
        monthly = monthly.sort_values("Month")
        monthly["Month"] = monthly["Month"].dt.strftime("%Y-%m")
        return monthly

    def render_monthly_chart(title: str, monthly_df: pd.DataFrame, total_label: str):
        st.markdown(f"#### {title}")
        if monthly_df.empty:
            st.caption("No data available yet.")
            return

        chart_data = monthly_df.set_index("Month")
        st.bar_chart(chart_data)
        total_value = monthly_df["Amount"].sum()
        st.caption(f"{total_label}: €{total_value:,.2f}")

    st.markdown("---")
    st.markdown("### 📈 Income & Contributions Trends")

    interests_df = prepare_monthly_series(transactions_with_dates, "Interest")
    pension_df = prepare_monthly_series(transactions_with_dates, "Pension")
    dividends_df = prepare_monthly_series(transactions_with_dates, "Dividend")

    render_monthly_chart("Monthly Interest", interests_df, "Total Interest")

    st.markdown("#### Monthly Pension Contributions")
    pension_profit_dkk = st.number_input(
        "Pension contribution profit (DKK)",
        min_value=0.0,
        value=0.0,
        step=100.0,
        format="%.2f",
        help="Enter your profit in DKK to keep track of pension performance.",
    )
    if pension_df.empty:
        st.caption("No pension contributions recorded yet.")
    else:
        st.bar_chart(pension_df.set_index("Month"))
        st.caption(f"Total Pension Contributions: €{pension_df['Amount'].sum():,.2f}")

    st.caption(f"Reported Pension Profit: DKK {pension_profit_dkk:,.2f}")

    render_monthly_chart("Monthly Dividends", dividends_df, "Total Dividends")


def render_stock_view(stock_view_df: pd.DataFrame):
    """Render the stock-centric view with profit information."""
    st.subheader("📊 Stock View")

    if stock_view_df is None or stock_view_df.empty:
        logger.info("Stock view data frame is empty")
        st.info("ℹ️ No stock data available to display.")
        return

    available_names = stock_view_df["Name"].dropna().unique()
    if len(available_names) == 0:
        logger.info("No valid stock names present in stock view data frame")
        st.info("ℹ️ No stock data available to display.")
        return

    selected_name = st.selectbox(
        "Select a stock to review",
        options=sorted(available_names),
        help="Choose a stock to see its weighted averages, current price and profit.",
    )

    selected_row = stock_view_df[stock_view_df["Name"] == selected_name]
    if selected_row.empty:
        logger.warning("Selected stock '%s' not found in data frame", selected_name)
        st.info("ℹ️ Unable to display details for the selected stock.")
        return

    selected_row = selected_row.iloc[0]

    def _format_currency(value: float) -> str:
        if pd.isna(value):
            return "—"
        return f"€{value:,.2f}"

    def _format_percentage(value: float) -> str:
        if pd.isna(value):
            return "—"
        return f"{value:+.2f}%"

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Weighted Avg Buy Price",
            _format_currency(selected_row.get("Weighted Avg Buy Price (EUR)")),
        )

    with col2:
        st.metric(
            "Current Price",
            _format_currency(selected_row.get("Current Price (EUR)")),
        )

    with col3:
        st.metric(
            "Weighted Avg Sell Price",
            _format_currency(selected_row.get("Weighted Avg Sell Price (EUR)")),
        )
        st.metric(
            "Profit",
            _format_currency(selected_row.get("Profit (EUR)")),
            _format_percentage(selected_row.get("Profit (%)")),
        )

    if pd.isna(selected_row.get("Current Price (EUR)")):
        st.caption(
            "Current price unavailable — add a manual price or ensure market data is accessible."
        )
    else:
        st.caption(
            "Prices are displayed per share in EUR. Profit combines realized and unrealized performance."
        )

    st.markdown("---")
    st.markdown("### 📚 All Stocks")
    st.caption(
        "Browse every tracked stock in alphabetical order. Use the selector above to focus on a single position, then scroll to review the complete list."
    )

    all_stocks_df = (
        stock_view_df.dropna(subset=["Name"])
        .sort_values("Name", key=lambda s: s.astype(str).str.lower())
        .reset_index(drop=True)
    )

    if all_stocks_df.empty:
        st.info("ℹ️ No additional stock details available to display.")
        return

    for start in range(0, len(all_stocks_df), 3):
        columns = st.columns(3, gap="large")
        for column, (_, stock_row) in zip(
            columns, all_stocks_df.iloc[start : start + 3].iterrows()
        ):
            with column:
                st.markdown(f"**{stock_row['Name']}**")
                st.metric(
                    "Profit",
                    _format_currency(stock_row.get("Profit (EUR)")),
                    _format_percentage(stock_row.get("Profit (%)")),
                )
                st.caption(
                    " | ".join(
                        [
                            f"Avg Buy: {_format_currency(stock_row.get('Weighted Avg Buy Price (EUR)'))}",
                            f"Avg Sell: {_format_currency(stock_row.get('Weighted Avg Sell Price (EUR)'))}",
                        ]
                    )
                )
                st.caption(
                    " | ".join(
                        [
                            f"Current Price: {_format_currency(stock_row.get('Current Price (EUR)'))}",
                            f"Current Value: {_format_currency(stock_row.get('Current Value (EUR)'))}",
                        ]
                    )
                )


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
