# Investment Portfolio Tracker

A modular, clean Streamlit application to track and visualize your personal investment portfolio with real-time stock prices and currency conversions.

## ✨ Features

- 📊 Connect to Google Sheets for transaction data
- 💹 Real-time stock price fetching via Yahoo Finance
- 💱 Multi-currency support (USD, EUR, DKK, CAD, etc.)
- 📈 Calculate returns and performance metrics
- 🏠 Support for custom investments (Real Estate, Pension, etc.)
- 📥 Export portfolio reports to CSV
- 🔐 Privacy-first: credentials never stored or shared

## 🏗️ Project Architecture

This project follows clean code principles with a modular architecture:

```
investment-portfolio-tracker/
├── app.py                  # Entry point (minimal logic)
├── core/                   # Business logic
│   └── portfolio.py        # Portfolio calculations
├── data/                   # Data access layer
│   ├── google_sheets.py    # Google Sheets client
│   └── market_data.py      # Market data provider
├── ui/                     # User interface
│   ├── layout.py           # Main layout
│   └── components.py       # UI components
└── utils/                  # Utilities
    └── session.py          # Session management
```

See [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for detailed documentation.

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- [UV](https://github.com/astral-sh/uv) package manager
- Google Cloud Project with Sheets API enabled
- Google Sheet with transaction data

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd investment-portfolio-tracker
```

### 2. Install Dependencies with UV

```bash
# Install UV if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .
```

### 3. Set Up Google Sheets API

#### a) Create a Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable the **Google Sheets API** for your project

#### b) Create Service Account Credentials
1. Go to **IAM & Admin** > **Service Accounts**
2. Click **Create Service Account**
3. Give it a name (e.g., "portfolio-tracker")
4. Click **Create and Continue**
5. Skip granting roles (optional)
6. Click **Done**
7. Click on the created service account
8. Go to **Keys** tab
9. Click **Add Key** > **Create New Key**
10. Choose **JSON** format
11. Download the JSON file

⚠️ **IMPORTANT**: Keep this JSON file secure! Add it to `.gitignore` and never commit it to version control.

#### c) Share Your Google Sheet
1. Open your Google Sheet named "Transactions"
2. Click the **Share** button
3. Add the service account email from the JSON file (looks like: `xxx@xxx.iam.gserviceaccount.com`)
4. Give it **Viewer** access
5. Click **Send**

### 4. Prepare Your Google Sheet

Your Google Sheet should be named **"Transactions"** and have a tab also named **"Transactions"** with these columns:

| Column | Description | Example |
|--------|-------------|---------|
| Ticker | Stock symbol or investment name | AAPL, TSLA, "Real Estate #1" |
| Type | Transaction type | BUY, SELL, DIVIDEND |
| Quantity | Number of shares/units | 10 |
| Price | Price per share/unit | 150.50 |
| Currency | Currency code | USD, EUR, DKK, CAD |
| Date | Transaction date (optional) | 2024-01-15 |

**Example rows:**

```
Ticker          | Type     | Quantity | Price    | Currency | Date
AAPL            | BUY      | 10       | 150.00   | USD      | 2024-01-15
GOOGL           | BUY      | 5        | 140.00   | USD      | 2024-02-01
ASML            | BUY      | 2        | 850.00   | EUR      | 2024-03-10
AAPL            | DIVIDEND | 0        | 2.50     | USD      | 2024-06-15
Real Estate #1  | BUY      | 1        | 50000.00 | EUR      | 2023-12-01
```

You can import `Sample_Transactions.csv` as a starting point.

### 5. Run the Application

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## 🔐 Security & Privacy

### Credentials Are Never Stored

- Your Google Service Account credentials are **only used in your browser session**
- Credentials are **never** saved to disk or sent to external servers
- All API calls are made **directly from your machine**
- The `.gitignore` file is configured to prevent accidental commits of sensitive files

### Best Practices

1. **Never commit credentials**: The `.gitignore` protects `*.json` files
2. **Restrict service account permissions**: Only give "Viewer" access to your sheet
3. **Keep credentials local**: Store the JSON file outside the project directory
4. **Use Streamlit secrets for deployment**: See deployment section below

## 📖 Usage Guide

### First Time Setup

1. **Paste Credentials**: In the sidebar, paste the entire contents of your Google Service Account JSON file
2. **Enter Sheet Name**: Confirm or modify the Google Sheet name (default: "Transactions")
3. **Click Refresh**: The app will load your transactions and fetch current market data

### Understanding the Dashboard

#### Summary Metrics
- **Total Invested**: Total amount invested across all positions (in EUR)
- **Current Value**: Current market value of your portfolio (in EUR)
- **Total Returns**: Absolute return in EUR with percentage
- **Active Positions**: Number of current holdings

#### Manual Value Input
For investments without stock tickers (Real Estate, Pension funds, etc.):
- The sidebar will prompt you to enter current values
- Values are stored in your session (not persisted)
- Update values and click "Refresh Data" to recalculate

#### Portfolio Table
- **Green values**: Positive returns
- **Red values**: Negative returns
- Sortable by clicking column headers
- Download as CSV for record-keeping

## 🛠️ Development

### Running Tests
```bash
# TODO: Add tests
uv pip install pytest
pytest
```

### Code Style
```bash
# Install dev dependencies
uv pip install ruff black

# Format code
black .

# Lint code
ruff check .
```

### Adding New Features

The modular architecture makes it easy to extend:

- **New data sources**: Add to `data/` directory
- **New UI components**: Add to `ui/components.py`
- **New calculations**: Add to `core/portfolio.py`
- **New market data providers**: Extend `data/market_data.py`

## 🚢 Deployment

### Streamlit Cloud

1. Push your code to GitHub (ensure `.gitignore` is working!)
2. Go to [Streamlit Cloud](https://streamlit.io/cloud)
3. Create a new app from your repository
4. Add secrets in **Settings** > **Secrets**:

```toml
# .streamlit/secrets.toml (don't commit this!)
[google_credentials]
type = "service_account"
project_id = "your-project-id"
private_key_id = "your-key-id"
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "your-service-account@project.iam.gserviceaccount.com"
client_id = "your-client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "your-cert-url"
```

5. Update `app.py` to use secrets:

```python
# In app.py, replace credentials input with:
if st.secrets.get("google_credentials"):
    credentials_dict = dict(st.secrets["google_credentials"])
else:
    # Fallback to manual input for local development
    credentials_json = st.sidebar.text_area(...)
```

## ❓ Troubleshooting

### "Error connecting to Google Sheets"
- Verify your JSON credentials are valid and properly formatted
- Ensure the Google Sheets API is enabled in your Google Cloud project
- Check that you've pasted the complete JSON (starts with `{` and ends with `}`)

### "Error loading transactions"
- Check that your Google Sheet is named correctly
- Verify the service account has access to the sheet (check the "Share" settings)
- Ensure there's a tab named "Transactions" in your sheet

### "Could not fetch price for [ticker]"
- Some tickers might not be available on Yahoo Finance
- Verify the ticker symbol is correct (e.g., use `NOVO-B.CO` for Danish stocks)
- For custom investments, you'll need to provide manual values in the sidebar

### Exchange Rate Issues
- The app uses a free API with rate limits
- If rates fail to load, it defaults to 1.0 (assumes EUR)
- Consider implementing a backup exchange rate API

### UV Installation Issues
```bash
# If UV command not found after installation
export PATH="$HOME/.cargo/bin:$PATH"

# Or reinstall
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## 🗺️ Roadmap

Planned features:
- [ ] Historical performance charts and trends
- [ ] Asset allocation visualization (pie/donut charts)
- [ ] Benchmark comparison (S&P 500, MSCI World)
- [ ] Multiple portfolios support
- [ ] Tax loss harvesting suggestions
- [ ] Dividend tracking and projections
- [ ] Export to PDF reports
- [ ] Dark mode support
- [ ] Mobile-responsive design improvements

## 📄 License

This is a personal project for portfolio tracking. Feel free to fork and adapt it to your needs.

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Follow the existing code structure
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

For issues or questions:
- Open an issue on GitHub
- Check existing issues for solutions
- Review the troubleshooting section

---

**⚠️ Disclaimer**: This tool is for informational purposes only. It does not constitute financial advice. Always consult with a qualified financial advisor before making investment decisions.