# Finance Integration Dashboard

A comprehensive Flask application for financial data analysis and visualization of coffee and beverage companies.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.0%2B-green.svg)](https://flask.palletsprojects.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-1.4-orange.svg)](https://sqlalchemy.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Features

- Multi-source financial data with automatic fallbacks (Finnhub → Yahoo Finance → Hardcoded)
- Real-time stock tracking with technical indicators and earnings analysis
- Sentiment analysis of financial news using NLTK
- Interactive Plotly dashboards with responsive design
- Smart caching and automated ETL pipelines
- Performance-optimized database with intelligent indexing
- CSV export and multi-stock comparison views

## Quick Start

### Prerequisites
- Python 3.10+
- PostgreSQL (recommended) or SQLite
- API Keys: [Finnhub](https://finnhub.io/), [Alpha Vantage](https://www.alphavantage.co/)

### Installation

```bash
git clone https://github.com/mseijse01/finance-integration.git
cd finance-integration
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python utils/setup_nltk.py

# Setup environment
cp .env.example .env
# Edit .env with your API keys and database URL

# Initialize and run
flask run-etl
python app.py
# Access dashboard at http://localhost:5000
```

## Supported Stocks

**Coffee & Beverage Companies:** SBUX, KDP, BROS, FARM

*Add new symbols to `coffee_stocks` list in `views/dashboard.py`*

## Usage

### Running ETL
```bash
# Manual ETL runs
python scripts/schedule_etl.py --run-once              # All stocks
python scripts/schedule_etl.py --run-once --symbols SBUX  # Single stock

# Check data freshness
python scripts/schedule_etl.py --check-freshness

# Set up automated daily updates
python scripts/schedule_etl.py --create-cron
```

### Performance Optimization
```bash
# Add database indexes for faster queries (50-70% improvement)
python scripts/add_performance_indexes.py

# Migrate database schema if needed
python scripts/migrate_database_schema.py
```

## Deployment

### Docker
```bash
docker build -t finance-integration .
docker run -p 8000:5000 --env-file .env finance-integration
```

### Manual
```bash
export DATABASE_URL=postgresql://user:pass@host:5432/finance_db
export FINNHUB_API_KEY=your_key
export ALPHA_VANTAGE_API_KEY=your_key
python app.py
```

## Documentation

- [Service Architecture](documentation/service_architecture.md) - BaseDataService pattern and intelligent fallbacks
- [Technology Stack](documentation/technology_stack.md) - Technology choices and rationale
- [Quick Start Guide](documentation/quick_start_guide.md) - Comprehensive usage guide

## Recent Improvements

- Automated ETL scheduling system with cron integration
- Database performance optimization with intelligent indexing (50-70% faster queries)
- Modular chart utilities for improved code organization
- Enhanced service architecture with BaseDataService pattern

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

[Report Bug](https://github.com/mseijse01/finance-integration/issues) • [Request Feature](https://github.com/mseijse01/finance-integration/issues) • [Documentation](documentation/) • [Quick Start Guide](documentation/quick_start_guide.md)
