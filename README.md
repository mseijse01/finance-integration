# 📈 Finance Integration Dashboard

A data-driven Flask web application that tracks and visualizes stock prices, financial fundamentals, earnings, and sentiment analysis for cannabis-related companies.

This project showcases a robust ETL pipeline, API integrations (Alpha Vantage & Finnhub), database handling with SQLAlchemy, and dynamic dashboards powered by Plotly — all structured for modularity and scalability.

## 🚀 Features

- 📰 **News Sentiment** from the past 30 days via Finnhub
- 📊 **Interactive Stock Charts** with moving averages and volatility
- 📉 **Financial Fundamentals** (Revenue, Net Income, EPS, Earnings Date)
- 🔁 **ETL Pipeline** for fetching, transforming, and loading historical stock data
- 📥 **CSV Download** for both raw and transformed stock data
- 🗃️ **SQLAlchemy ORM** and PostgreSQL backend
- 📦 Ready for future **Machine Learning** (e.g., price prediction)

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
├── services/                ← API data fetching
│   ├── news.py
│   ├── financials.py
│   └── earnings.py
│
├── views/                   ← Flask route logic
│   ├── dashboard.py
│   └── news.py
│
├── etl/                     ← ETL pipeline components
│   ├── extraction.py
│   ├── transformation.py
│   └── loading.py
│
├── ml/                      ← Placeholder for future ML modules
│   └── predictor.py
│
├── utils/                   ← Logging and plotting helpers
│   ├── logging_config.py
│   └── plot_helpers.py
│
├── templates/               ← Jinja2 templates
│   ├── base.html
│   ├── dashboard.html
│   └── news.html
│
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

5. Run the application

## 🔄 Data Flow

1. **Extract**: Fetch stock data from Alpha Vantage and news/sentiment from Finnhub
2. **Transform**: Process and normalize the data for database storage
3. **Load**: Store in PostgreSQL database via SQLAlchemy models
4. **Visualize**: Generate interactive charts with Plotly through Flask routes
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
