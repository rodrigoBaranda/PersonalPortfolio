"""
UI Components
Reusable UI components for the Streamlit application
"""
from datetime import datetime
import html
import textwrap

import pandas as pd
import streamlit as st

from data.market_data import MarketDataProvider
from utils import get_logger


logger = get_logger(__name__)
market_data_provider = MarketDataProvider()


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

    manual_values = st.session_state.setdefault("manual_values", {})

    normalized_manual_values = {}
    for ticker_key, value in manual_values.items():
        if isinstance(value, dict):
            price = value.get("price")
            currency = value.get("currency")
        else:
            price = value
            currency = "EUR"

        try:
            price = float(price) if price is not None else None
        except (TypeError, ValueError):
            logger.debug(
                "Skipping normalization for ticker '%s' due to invalid price '%s'",
                ticker_key,
                price,
            )
            price = None

        if isinstance(currency, str):
            currency = currency.strip().upper() or None

        normalized_manual_values[ticker_key] = {
            "price": price,
            "currency": currency,
        }

    st.session_state["manual_values"] = normalized_manual_values
    manual_values = normalized_manual_values

    missing_price_series = (
        summary_df["Current Price (EUR)"].isna()
        if "Current Price (EUR)" in summary_df.columns
        else pd.Series(False, index=summary_df.index)
    )

    open_positions_series = (
        summary_df["Position Status"].eq("Open")
        if "Position Status" in summary_df.columns
        else pd.Series(True, index=summary_df.index, dtype=bool)
    )

    interest_names: set = set()
    if (
        transactions_df is not None
        and not transactions_df.empty
        and {"name", "type"}.issubset(transactions_df.columns)
    ):
        interest_mask = (
            transactions_df["type"].astype(str).str.strip().str.lower() == "interest"
        )
        interest_names = set(
            transactions_df.loc[interest_mask, "name"].dropna().astype(str).unique()
        )

    is_interest_summary = (
        summary_df["Name"].astype(str).isin(interest_names)
        if "Name" in summary_df.columns and interest_names
        else pd.Series(False, index=summary_df.index)
    )

    manual_candidate_mask = (
        missing_price_series & open_positions_series & ~is_interest_summary
    )

    if manual_candidate_mask.any():
        st.markdown("### ✏️ Update Missing Prices")
        st.caption(
            "Provide the latest price for each open position in the currency shown below. Highlighted rows in the table correspond to these entries."
        )

        editor_columns = [
            col
            for col in ["Name", "Ticker", "Currency", "Current Price (EUR)"]
            if col in summary_df.columns
        ]
        manual_editor_df = summary_df.loc[manual_candidate_mask, editor_columns].copy()

        if "Ticker" not in manual_editor_df.columns:
            manual_editor_df.insert(1, "Ticker", manual_editor_df["Name"])

        if "Currency" not in manual_editor_df.columns:
            manual_editor_df.insert(2, "Currency", "EUR")

        manual_editor_df.rename(columns={"Currency": "Input Currency"}, inplace=True)

        if "Current Price (EUR)" in manual_editor_df.columns:
            manual_editor_df.drop(columns=["Current Price (EUR)"], inplace=True)

        manual_editor_df["Manual Price"] = pd.Series(
            [None] * len(manual_editor_df),
            index=manual_editor_df.index,
            dtype="float64",
        )

        def _apply_price_to_summary(
            ticker_value: str, name_value: str, price_value_eur: float
        ):
            if pd.isna(price_value_eur):
                return
            if "Ticker" in summary_df.columns:
                summary_df.loc[
                    summary_df["Ticker"] == ticker_value, "Current Price (EUR)"
                ] = float(price_value_eur)
            else:
                summary_df.loc[
                    summary_df["Name"] == name_value, "Current Price (EUR)"
                ] = float(price_value_eur)

        for idx, row in manual_editor_df.iterrows():
            ticker = row.get("Ticker")
            currency = row.get("Input Currency") or "EUR"
            if isinstance(currency, str):
                currency = currency.strip().upper() or "EUR"
            if ticker in manual_values:
                manual_entry = manual_values.get(ticker, {})
                manual_price = manual_entry.get("price")
                manual_currency = manual_entry.get("currency") or "EUR"
                if manual_price is not None:
                    if manual_currency != currency and manual_currency and currency:
                        try:
                            rate_to_eur = market_data_provider.get_exchange_rate(
                                manual_currency, "EUR"
                            )
                            if currency == "EUR":
                                converted_price = manual_price * rate_to_eur
                            else:
                                rate_from_eur = market_data_provider.get_exchange_rate(
                                    "EUR", currency
                                )
                                converted_price = manual_price * rate_to_eur * rate_from_eur
                        except Exception:
                            logger.exception(
                                "Failed to convert manual price for ticker '%s'", ticker
                            )
                            converted_price = manual_price
                    else:
                        converted_price = manual_price

                    try:
                        manual_editor_df.at[idx, "Manual Price"] = float(converted_price)
                    except (TypeError, ValueError):
                        manual_editor_df.at[idx, "Manual Price"] = converted_price

                    price_eur = manual_price
                    if manual_currency and manual_currency != "EUR":
                        price_eur = manual_price * market_data_provider.get_exchange_rate(
                            manual_currency, "EUR"
                        )

                    _apply_price_to_summary(ticker, row.get("Name"), price_eur)

        st.markdown(
            """
            <style>
            div[data-testid="stDataFrame"][data-st-key="summary_price_editor"] {
                background-color: #f1f3f5;
                border-radius: 0.75rem;
                padding: 1rem;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        with st.form("manual_price_form"):
            edited_manual_df = st.data_editor(
                manual_editor_df,
                column_config={
                    "Name": st.column_config.TextColumn("Name", disabled=True),
                    "Ticker": st.column_config.TextColumn(
                        "Ticker",
                        disabled=True,
                        help="Identifier used for manual price overrides.",
                    ),
                    "Input Currency": st.column_config.TextColumn(
                        "Currency",
                        disabled=True,
                        help="Currency detected from your transactions for this position.",
                    ),
                    "Manual Price": st.column_config.NumberColumn(
                        "Current Price",
                        help=(
                            "Provide the latest price per share in the displayed currency."
                        ),
                        min_value=0.0,
                        step=0.01,
                        format="%.2f",
                        required=True,
                    ),
                },
                hide_index=True,
                key="summary_price_editor",
                num_rows="fixed",
            )
            submitted = st.form_submit_button("Save Price Updates")

        if submitted:
            for _, row in edited_manual_df.iterrows():
                ticker = row.get("Ticker")
                price = row.get("Manual Price")
                currency = row.get("Input Currency") or "EUR"
                if isinstance(currency, str):
                    currency = currency.strip().upper() or "EUR"
                if not ticker:
                    continue
                if pd.notna(price) and float(price) > 0:
                    numeric_price = float(price)
                    manual_values[ticker] = {
                        "price": numeric_price,
                        "currency": currency,
                    }

                    price_eur = numeric_price
                    if currency and currency != "EUR":
                        price_eur *= market_data_provider.get_exchange_rate(
                            currency, "EUR"
                        )

                    _apply_price_to_summary(ticker, row.get("Name"), price_eur)
                elif ticker in manual_values:
                    manual_values.pop(ticker)

            st.success("Manual price updates saved.")

    formatted_df = summary_df.style.format({
        "Purchased Times": "{:.0f}",
        "Number of Shares": "{:.2f}",
        "Total Invested (EUR)": "€{:,.2f}",
        "Weighted Avg Buy Price (EUR)": "€{:,.2f}",
        "Weighted Avg Sell Price (EUR)": "€{:,.2f}",
        "Current Price (EUR)": "€{:,.2f}",
        "Current Open Amount EUR": "€{:,.2f}",
    })

    highlight_indices = set(summary_df.index[manual_candidate_mask])

    def _highlight_row(row: pd.Series):
        styles = [""] * len(row)

        status = row.get("Position Status")
        if isinstance(status, str) and status.strip().lower() == "closed":
            styles = ["background-color: #fbf5ff"] * len(row)

        if row.name in highlight_indices:
            styles = [
                f"{style}; background-color: #f1f3f5" if style else "background-color: #f1f3f5"
                for style in styles
            ]

        return styles

    formatted_df = formatted_df.apply(_highlight_row, axis=1)

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

    st.markdown(
        textwrap.dedent(
            """
            <style>
            .stock-section {
                border-radius: 1rem;
                padding: 1.25rem;
                margin-bottom: 1.5rem;
            }
            .stock-section.open {
                background: linear-gradient(135deg, #eef8ff 0%, #f6fbff 100%);
            }
            .stock-section.closed {
                background: linear-gradient(135deg, #f7f1ff 0%, #fbf5ff 100%);
            }
            .stock-section h4 {
                margin-top: 0;
            }
            .stock-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
                gap: 1rem;
                margin-top: 1rem;
            }
            .stock-card {
                background: white;
                border-radius: 0.85rem;
                padding: 1rem;
                box-shadow: 0 4px 12px rgba(15, 23, 42, 0.08);
                display: flex;
                flex-direction: column;
                gap: 0.5rem;
            }
            .stock-card.closed {
                background: #fff8ff;
            }
            .stock-card__header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                font-weight: 600;
            }
            .stock-card__label {
                font-size: 0.8rem;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                color: #6b7280;
            }
            .stock-card__value {
                font-weight: 600;
                color: #111827;
            }
            .stock-card__metric {
                display: flex;
                justify-content: space-between;
                align-items: center;
                font-size: 0.95rem;
            }
            .stock-card__profit-positive {
                color: #0f9d58;
            }
            .stock-card__profit-negative {
                color: #d93025;
            }
            </style>
            """
        ),
        unsafe_allow_html=True,
    )

    def _render_stock_cards(section_title: str, section_df: pd.DataFrame, section_class: str):
        st.markdown(f"<div class='stock-section {section_class}'>", unsafe_allow_html=True)
        st.markdown(f"<h4>{html.escape(section_title)}</h4>", unsafe_allow_html=True)

        if section_df.empty:
            st.markdown("<p>No positions in this category yet.</p>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            return

        cards_html = []
        for _, stock_row in section_df.iterrows():
            profit_value = _format_currency(stock_row.get("Profit (EUR)"))
            profit_pct_value = _format_percentage(stock_row.get("Profit (%)"))
            profit_class = "stock-card__profit-positive"
            profit_number = stock_row.get("Profit (EUR)")
            if pd.isna(profit_number) or profit_number == 0:
                profit_class = ""
            elif profit_number < 0:
                profit_class = "stock-card__profit-negative"

            card_html = textwrap.dedent(
                f"""
                <div class="stock-card {'closed' if stock_row.get('Position Status') == 'Closed' else ''}">
                    <div class="stock-card__header">
                        <span>{html.escape(str(stock_row.get('Name', '—')))}</span>
                        <span class="stock-card__label">{html.escape(str(stock_row.get('Position Status', '—')))}</span>
                    </div>
                    <div class="stock-card__metric">
                        <span class="stock-card__label">Profit</span>
                        <span class="stock-card__value {profit_class}">{html.escape(profit_value)} ({html.escape(profit_pct_value)})</span>
                    </div>
                    <div class="stock-card__metric">
                        <span class="stock-card__label">Avg Buy</span>
                        <span class="stock-card__value">{html.escape(_format_currency(stock_row.get('Weighted Avg Buy Price (EUR)')))}</span>
                    </div>
                    <div class="stock-card__metric">
                        <span class="stock-card__label">Avg Sell</span>
                        <span class="stock-card__value">{html.escape(_format_currency(stock_row.get('Weighted Avg Sell Price (EUR)')))}</span>
                    </div>
                    <div class="stock-card__metric">
                        <span class="stock-card__label">Current Price</span>
                        <span class="stock-card__value">{html.escape(_format_currency(stock_row.get('Current Price (EUR)')))}</span>
                    </div>
                    <div class="stock-card__metric">
                        <span class="stock-card__label">Current Value</span>
                        <span class="stock-card__value">{html.escape(_format_currency(stock_row.get('Current Value (EUR)')))}</span>
                    </div>
                </div>
                """
            ).strip()
            cards_html.append(card_html)

        st.markdown(
            f"<div class='stock-grid'>{''.join(cards_html)}</div>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    open_positions = all_stocks_df[all_stocks_df["Position Status"] == "Open"]
    closed_positions = all_stocks_df[all_stocks_df["Position Status"] == "Closed"]

    _render_stock_cards("Open Positions", open_positions, "open")
    _render_stock_cards("Closed Positions", closed_positions, "closed")


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
