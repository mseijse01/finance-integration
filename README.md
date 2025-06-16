# Finance Integration Dashboard

> **A comprehensive Flask application for financial data analysis and visualization**

Track and visualize stock prices, financial fundamentals, earnings, and sentiment analysis for coffee and beverage companies. Features robust data pipelines, intelligent caching, and beautiful interactive dashboards built with modern web technologies.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.0%2B-green.svg)](https://flask.palletsprojects.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-1.4-orange.svg)](https://sqlalchemy.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## **Key Features**

- **Multi-source financial data** with automatic fallbacks (Finnhub → Yahoo Finance → Hardcoded)
- **Real-time stock tracking** with technical indicators and earnings analysis
- **Sentiment analysis** of financial news using NLTK
- **Interactive Plotly dashboards** with responsive design
- **Smart caching** and background ETL for optimal performance
- **CSV export** and multi-stock comparison views

---

## **Architecture**

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│    User     │───▶│   Flask     │───▶│  Services   │───▶│  Response   │
│  (Browser)  │    │   Routes    │    │   Layer     │    │   (JSON)    │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                                             │
                                             ▼
                   ┌─────────────────────────────────────────────────┐
                   │              Data Sources                       │
                   │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────┐ │
                   │  │Database │  │Finnhub  │  │ Yahoo   │  │Hard │ │
                   │  │(Cache)  │  │   API   │  │Finance  │  │coded│ │
                   │  │  [1]    │  │   [2]   │  │   [3]   │  │ [4] │ │
                   │  └─────────┘  └─────────┘  └─────────┘  └─────┘ │
                   └─────────────────────────────────────────────────┘
```

### **Data Source Priority**
1. **Database Cache** - Return cached data instantly if available
2. **Finnhub API** - Primary source for fresh financial data
3. **Yahoo Finance** - Backup when Finnhub is unavailable
4. **Hardcoded Data** - Fallback for stocks with limited API coverage

The ETL pipeline runs in the background to keep the database fresh, ensuring fast response times.

---

## **Quick Start**

### **Prerequisites**
- Python 3.10+
- PostgreSQL (recommended) or SQLite
- API Keys: [Finnhub](https://finnhub.io/), [Alpha Vantage](https://www.alphavantage.co/)

### **Installation**

```bash
git clone https://github.com/mseijse01/finance-integration.git
cd finance-integration
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python utils/setup_nltk.py

# Configure environment
cp .env.example .env
# Edit .env with your API keys and database URL

# Initialize and run
flask run-etl
python app.py
# Access dashboard at http://localhost:5000
```

---

## **Supported Stocks**

**Coffee & Beverage Companies:** SBUX, KDP, BROS, FARM

*Add new symbols to `coffee_stocks` list in `views/dashboard.py`*

---

## **Development**

### **Adding New Stocks**
```python
# In views/dashboard.py
coffee_stocks = ["SBUX", "KDP", "BROS", "FARM", "YOUR_SYMBOL"]
```

### **Running ETL**
```bash
flask run-etl --symbol=SBUX    # Single stock
flask run-etl                  # All stocks
```

---

## **Deployment**

### **Docker**
```bash
docker build -t finance-integration .
docker run -p 8000:5000 --env-file .env finance-integration
```

### **Manual**
```bash
export DATABASE_URL=postgresql://user:pass@host:5432/finance_db
export FINNHUB_API_KEY=your_key
export ALPHA_VANTAGE_API_KEY=your_key
python app.py
```

---

---

## **Recent Improvements**

- Enhanced service architecture with BaseDataService pattern and intelligent fallbacks
- Advanced caching strategies with adaptive TTL and background data loading
- Comprehensive error handling and graceful service degradation

> **Note:** This project is actively maintained with continuous improvements to performance and reliability.

---

## **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---



<div align="center">

**⭐ Star this repo if you find it useful! ⭐**

[Report Bug](https://github.com/mseijse01/finance-integration/issues) • [Request Feature](https://github.com/mseijse01/finance-integration/issues) • [Documentation](documentation/)

</div>
