# 📈 Finance Integration Dashboard

A data-driven Flask web application that tracks and visualizes stock prices, financial fundamentals, earnings, and sentiment analysis for cannabis-related companies.

This project showcases a robust ETL pipeline, API integrations (Alpha Vantage, Finnhub & Yahoo Finance), database handling with SQLAlchemy, and dynamic dashboards powered by Plotly — all structured for modularity and scalability.

## 🚀 Features

- 📰 **News Sentiment** from the past 30 days via Finnhub
- 📊 **Interactive Stock Charts** with moving averages and volatility
- 📉 **Financial Fundamentals** (Revenue, Net Income, EPS, Earnings Date)
  - Primary data source: Finnhub
  - Secondary data source: Yahoo Finance (for stocks without Finnhub coverage)
  - Tertiary data source: Hardcoded data from investor relations sites
  - Data source comparison when both sources available
- 🔁 **Comprehensive ETL Pipeline** for stock data, news, financials, and earnings
- 📥 **CSV Download** for both raw and transformed stock data
- 🗃️ **Smart Service Adapters** for resilient data access with graceful fallbacks
- 🔄 **Auto-Refresh** background processes for data currency
- 📊 **Responsive Design** for both desktop and mobile use
- 🌐 **NLTK Integration** for sentiment analysis of financial news

## 🏗️ Architecture

The application follows a clean architecture pattern:

1. **ETL Layer**: Extract, Transform, and Load data from external APIs into our database
2. **Service Adapters**: Smart adapters that attempt database access first, then trigger ETL if needed, with multiple fallback sources
3. **Data Access Layer**: Database models and query functions
4. **Presentation Layer**: Flask routes and Plotly visualizations

### Data Flow & Multi-Source Strategy

```
                           ┌──────────────────────┐
                           │   Database (Primary) │
                           └──────────┬───────────┘
                                      │
                                      ▼
┌─────────────────┐         ┌──────────────────────┐
│     User UI     │◀───────▶│   Service Adapters   │
└─────────────────┘         └──────────┬───────────┘
                                      │
                                      ▼
                            ┌─────────────────────┐
                            │  Database Missing?  │─── Yes ───┐
                            └─────────────────────┘           │
                                      │                       ▼
                                     No                ┌─────────────┐
                                      │                │  ETL Layer  │
                                      ▼                └──────┬──────┘
                           ┌──────────────────────┐           │
                           │      Return Data     │           ▼
                           └──────────────────────┘   ┌───────────────────┐
                                                      │  Finnhub API      │
                                                      │  (Primary API)    │
                                                      └────────┬──────────┘
                                                               │
                                                               ▼
                                                      ┌───────────────────┐
                                                      │  Data Available?  │─── Yes ───┐
                                                      └───────────────────┘           │
                                                               │                      ▼
                                                              No             ┌──────────────────┐
                                                               │             │ Store in Database│
                                                               ▼             └─────────┬────────┘
                                                      ┌───────────────────┐            │
                                                      │  Yahoo Finance    │            │
                                                      │  (Secondary API)  │            │
                                                      └────────┬──────────┘            │
                                                               │                       │
                                                               ▼                       │
                                                      ┌───────────────────┐            │
                                                      │  Data Available?  │─── Yes ────┘
                                                      └───────────────────┘
                                                               │
                                                              No
                                                               ▼
                                                      ┌───────────────────┐
                                                      │  Hardcoded Data   │
                                                      │  (Last Resort)    │
                                                      └────────┬──────────┘
                                                               │
                                                               ▼
                                                      ┌───────────────────┐
                                                      │  Data Available?  │─── Yes ────┐
                                                      └───────────────────┘            │
                                                               │                       ▼
                                                              No               ┌───────────────────┐
                                                               │               │   Return Data     │
                                                               ▼               └───────────────────┘
                                                      ┌───────────────────┐
                                                      │  Show User Message│
                                                      └───────────────────┘
```

## 🛠️ Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/mseijse01/finance-integration.git
    cd finance-integration
    ```

2. Set up virtual environment:
    ```bash
    python -m venv venv
    source .venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

4. Set up NLTK resources (resolves SSL certificate issues):
    ```bash
    python utils/setup_nltk.py
    ```

5. Set environment variables:
    ```bash
    export ALPHA_VANTAGE_API_KEY=your_api_key
    export FINNHUB_API_KEY=your_api_key
    export DATABASE_URL=postgresql://username:password@localhost:5432/finance_db
    ```

6. Run the ETL pipeline to fill the database:
    ```bash
    flask run-etl
    ```

## 🚀 Running the Application

Start the Flask application:
```bash
python app.py
```

Access the dashboard at http://localhost:5000

## 📦 Project Structure

```
finance-integration/
├── app.py                 # Flask application entry point
├── config.py              # Configuration settings
├── requirements.txt       # Project dependencies
├── run_etl.py             # ETL pipeline runner
├── etl/                   # ETL modules
│   ├── stock_etl.py       # Stock data ETL
│   ├── news_etl.py        # News data ETL
│   ├── financials_etl.py  # Financial data ETL
│   ├── earnings_etl.py    # Earnings data ETL
├── models/                # Data models
│   └── db_models.py       # SQLAlchemy models
├── services/              # Service adapters
│   ├── stocks.py          # Stock data service
│   ├── news.py            # News service
│   ├── financials.py      # Financials service
│   ├── earnings.py        # Earnings service
│   ├── alternative_financials.py # Yahoo Finance integration
│   └── hardcoded_financials.py  # Hardcoded data for exceptional cases
├── views/                 # Flask views/routes
│   ├── dashboard.py       # Main dashboard view
│   └── news.py            # News view
├── utils/                 # Utility functions
│   ├── cache.py           # Caching utilities
│   ├── data_processing.py # Data processing helpers
│   └── logging_config.py  # Logging configuration
├── static/                # Static assets (CSS, JS)
└── templates/             # Jinja2 templates
```

## 📊 Dashboard Features

- **Stock Price Chart**: Interactive visualization with adjustable timeframe
- **Financial Metrics**: Revenue, net income, and earnings data
- **News Sentiment**: Aggregated news with sentiment analysis
- **Compare Stocks**: View multiple cannabis stocks side-by-side
- **Data Source Attribution**: See which data source is being used for transparency
- **Data Source Comparison**: Compare financial metrics between different data providers
- **Maximum Data Coverage**: Multi-layered approach ensures data is available even for hard-to-cover stocks

## 🔄 Switching to Production

1. Configure a production database:
    ```bash
    export DATABASE_URL=postgresql://user:pass@production-db-host:5432/finance_db
    ```

2. Set up Gunicorn:
    ```bash
    gunicorn --workers=4 --bind=0.0.0.0:8000 app:app
    ```

3. Set up a reverse proxy (Nginx recommended)

## 🧑‍💻 Development

### Adding a New Stock

Edit `views/dashboard.py` and add the ticker to the `cannabis_stocks` list.

### Adding Hardcoded Financial Data

For stocks with limited API coverage, add hardcoded data to `services/hardcoded_financials.py`.

### Custom ETL Run

Run ETL pipeline for a specific stock:
```bash
flask run-etl --symbol=CGC
```

## 📚 Documentation

- [API Documentation](documentation/api.md)
- [ETL Pipeline](documentation/etl_pipeline.md)
- [Yahoo Finance Integration](documentation/yahoo_finance_integration.md)

## 📜 License

MIT License - See LICENSE file for details.
