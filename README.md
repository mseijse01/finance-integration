# 📈 Finance Integration Dashboard

A data-driven Flask web application that tracks and visualizes stock prices, financial fundamentals, earnings, and sentiment analysis for cannabis-related companies.

This project showcases a robust ETL pipeline, API integrations (Alpha Vantage & Finnhub), database handling with SQLAlchemy, and dynamic dashboards powered by Plotly — all structured for modularity and scalability.

## 🚀 Features

- 📰 **News Sentiment** from the past 30 days via Finnhub
- 📊 **Interactive Stock Charts** with moving averages and volatility
- 📉 **Financial Fundamentals** (Revenue, Net Income, EPS, Earnings Date)
- 🔁 **Comprehensive ETL Pipeline** for stock data, news, financials, and earnings
- 📥 **CSV Download** for both raw and transformed stock data
- 🗃️ **SQLAlchemy ORM** and PostgreSQL backend
- 📦 Ready for future **Machine Learning** (e.g., price prediction)
- 🔄 **Multi-layered Architecture** with adapters and fallback mechanisms

## 🧱 Project Structure

```
finance-integration/
├── app.py                    ← Flask application entry point
├── config.py                 ← Config loader for .env variables
├── .env                      ← API keys and database credentials (excluded from Git)
│
├── models/                  ← Database models
│   └── db_models.py
│
├── services/                ← Service adapters with fallback mechanisms
│   ├── README.md            ← Documentation of service architecture
│   ├── news.py              ← News data adapter (DB → ETL → API)
│   ├── financials.py        ← Financials adapter (DB → ETL → API)
│   └── earnings.py          ← Earnings adapter (DB → ETL → API)
│
├── views/                   ← Flask route logic
│   ├── dashboard.py
│   └── news.py
│
├── etl/                     ← ETL pipeline components
│   ├── extraction.py
│   ├── transformation.py
│   ├── loading.py
│   ├── news_etl.py          ← News ETL pipeline
│   ├── financials_etl.py    ← Financials ETL pipeline
│   └── earnings_etl.py      ← Earnings ETL pipeline
│
├── ml/                      ← Placeholder for future ML modules
│   └── predictor.py
│
├── utils/                   ← Logging and plotting helpers
│   ├── logging_config.py
│   ├── cache.py
│   └── plot_helpers.py
│
├── templates/               ← Jinja2 templates
│   ├── base.html
│   ├── dashboard.html
│   └── news.html
│
├── run_etl.py               ← Script to run all ETL pipelines
├── Dockerfile               ← Container definition
├── .dockerignore
├── requirements.txt
├── README.md
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

4. Set environment variables:
    ```bash
    export ALPHA_VANTAGE_API_KEY=your_api_key
    export FINNHUB_API_KEY=your_api_key
    export DATABASE_URL=postgresql://username:password@localhost:5432/finance_db
    ```

5. Run the ETL pipeline to fill the database:
    ```bash
    flask run-etl
    ```

6. Run the application:
    ```bash
    flask run
    ```

## 🔄 Data Flow

### ETL Pipeline Architecture

The application features a fully refactored ETL pipeline that centralizes all data operations:

1. **Stock Price ETL**
   - Extract: Fetch daily stock price data from Alpha Vantage API
   - Transform: Calculate moving averages, volatility, and normalize data
   - Load: Store in `stock_prices` table

2. **News ETL**
   - Extract: Fetch company news from Finnhub API
   - Transform: Perform sentiment analysis and normalize data
   - Load: Store in `news_articles` table with efficient upsert logic

3. **Financials ETL**
   - Extract: Fetch quarterly and annual financial reports from Finnhub API
   - Transform: Extract key metrics (revenue, net income, EPS) and normalize data
   - Load: Store in `financial_reports` table with proper relationships

4. **Earnings ETL**
   - Extract: Fetch earnings reports from Finnhub API
   - Transform: Calculate surprises, period information, and normalize data
   - Load: Store in `earnings` table with data validation

### Multi-layered Data Access Architecture

Our application implements a three-layered architecture for data access:

1. **ETL Pipelines** (Primary): Responsible for extracting, transforming, and loading data into the database
2. **Service Adapters**: Smart adapters that determine the best way to fetch data
3. **Direct API Access** (Fallback): Used only when database access fails

This provides:
- **Performance**: Most requests are served from the database
- **Freshness**: Stale data is automatically refreshed
- **Reliability**: Multiple fallback mechanisms
- **Backward Compatibility**: Legacy code continues to function

### Running the ETL Pipeline

The ETL pipeline can be run through the command line interface:

```bash
# Run ETL for all stock symbols
flask run-etl

# Run ETL for a specific symbol
flask run-etl --symbol CGC
```

### Dashboard Data Flow

1. **Database Queries**: Dashboard loads data from PostgreSQL database via SQLAlchemy models
2. **Caching**: Results are cached to improve performance and reduce API calls
3. **Parallel Processing**: Data for different stocks is loaded in parallel using threading
4. **Visualization**: Generate interactive charts with Plotly through Flask routes
5. **Download**: Export stock data as CSV files (raw or transformed) for offline analysis

## 📥 Data Download

Each stock on the dashboard includes two download options:

- **Download [SYMBOL] Data (CSV)**: Download the transformed dataset including calculated fields like moving averages and volatility
- **Download Raw Data**: Download the original API data without transformations

This feature allows data scientists and analysts to perform their own analysis using the raw or processed data.

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](https://github.com/mseijse01/finance-integration/issues).

## 📝 License

This project is [MIT](LICENSE) licensed.

## 🙋‍♂️ Author

Made by Marcelo Seijas
