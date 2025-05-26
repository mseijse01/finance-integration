# 📈 Finance Integration Dashboard

> **A sophisticated, production-ready Flask application for financial data analysis and visualization**

Track and visualize stock prices, financial fundamentals, earnings, and sentiment analysis for coffee and beverage companies with enterprise-grade data pipelines, intelligent caching, and beautiful interactive dashboards.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.0%2B-green.svg)](https://flask.palletsprojects.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-1.4-orange.svg)](https://sqlalchemy.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 🚧 **Current Status: Major Refactoring in Progress** 

**We are implementing a next-generation service architecture** to enhance modularity, maintainability, and scalability. During this transition:

- ✅ **Dual architecture** ensures zero downtime and full functionality
- ✅ **BaseDataService pattern** provides consistent, reusable service foundation  
- ✅ **Smart service adapters** enable seamless migration between old and new systems
- 🔄 **Gradual migration** maintains stability while improving architecture

### 🎯 Migration Progress
| Component | Status | Implementation |
|-----------|--------|----------------|
| **BaseDataService Foundation** | ✅ Complete | `base_service.py` |
| **Service Adapters** | ✅ Complete | `service_adapter.py` |
| **FinancialsService** | 🔄 Migrating | `refactored_financials.py` |
| **EarningsService** | 🔄 Migrating | `refactored_earnings.py` |
| **NewsService** | ⏳ Planned | Legacy functional |
| **StocksService** | ⏳ Planned | Legacy functional |
| **Legacy Cleanup** | ⏳ Post-migration | After completion |

---

## ✨ **Key Features**

### 📊 **Financial Data Intelligence**
- **Multi-source financial data** with automatic fallbacks (Finnhub → Yahoo Finance → Hardcoded)
- **Real-time stock price tracking** with technical indicators (moving averages, volatility)
- **Comprehensive earnings analysis** with surprise metrics and beat/miss tracking
- **Financial fundamentals** across quarterly and annual reporting periods

### 🧠 **Advanced Analytics**
- **Sentiment analysis** of financial news using NLTK
- **Data source comparison** for transparency and validation
- **Interactive visualizations** powered by Plotly
- **CSV data export** for external analysis

### 🏗️ **Enterprise Architecture**
- **Intelligent caching** with adaptive TTL and rate limiting
- **Resilient ETL pipelines** with parallel processing and error recovery
- **Background data refresh** for optimal performance
- **Thread-safe operations** with timeout handling

### 🎨 **User Experience**
- **Responsive design** optimized for desktop and mobile
- **Real-time dashboard** with auto-refresh capabilities
- **Multi-stock comparison** views
- **Data source attribution** for full transparency

---

## 🏗️ **Architecture Overview**

### **Clean Architecture Pattern**
```
┌─────────────────────────────────────────────────────────────────┐
│                        PRESENTATION LAYER                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Dashboard     │  │   News Views    │  │   API Routes    │ │
│  │   (Plotly)      │  │   (Sentiment)   │  │   (JSON/CSV)    │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────────┐
│                       SERVICE LAYER                            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ Service Adapter │  │ BaseDataService │  │ Legacy Services │ │
│  │ (Migration)     │  │ (New Pattern)   │  │ (Transitional)  │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────────┐
│                         ETL LAYER                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Extraction    │  │ Transformation  │  │    Loading      │ │
│  │ (Multi-source)  │  │ (Validation)    │  │ (Database)      │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────────┐
│                       DATA LAYER                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   PostgreSQL    │  │   Caching       │  │   External      │ │
│  │   (Primary)     │  │   (Redis-like)  │  │   APIs          │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### **Intelligent Data Flow with Multi-Source Fallbacks**

```mermaid
graph TD
    A[User Request] --> B[Service Adapter]
    B --> C{Database Check}
    
    C -->|Data Found| D[Return Cached Data]
    C -->|Data Missing/Stale| E[Trigger ETL Pipeline]
    
    E --> F{Finnhub API}
    F -->|Success| G[Transform & Store]
    F -->|Failed| H{Yahoo Finance API}
    
    H -->|Success| I[Transform & Store]
    H -->|Failed| J{Hardcoded Data}
    
    J -->|Available| K[Return Fallback Data]
    J -->|Not Available| L[Return Error Message]
    
    G --> M[Update Cache]
    I --> M
    M --> N[Return Fresh Data]
    
    style A fill:#e1f5fe
    style D fill:#c8e6c9
    style N fill:#c8e6c9
    style K fill:#fff3e0
    style L fill:#ffcdd2
```

---

## 🚀 **Quick Start**

### **Prerequisites**
- Python 3.10+
- PostgreSQL (recommended) or SQLite
- API Keys: [Finnhub](https://finnhub.io/), [Alpha Vantage](https://www.alphavantage.co/)

### **Installation**

1. **Clone and setup**
   ```bash
   git clone https://github.com/mseijse01/finance-integration.git
   cd finance-integration
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   python utils/setup_nltk.py  # Setup sentiment analysis
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and database URL
   export FINNHUB_API_KEY=your_finnhub_key
   export ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key
   export DATABASE_URL=postgresql://user:pass@localhost:5432/finance_db
   ```

4. **Initialize data**
   ```bash
   flask run-etl  # Populate database with initial data
   ```

5. **Launch application**
   ```bash
   python app.py
   # Access dashboard at http://localhost:5000
   ```

---

## 📁 **Project Structure**

```
finance-integration/
├── 🚀 app.py                          # Flask application entry point
├── ⚙️  config.py                       # Configuration management
├── 📋 requirements.txt                 # Python dependencies
├── 🔄 run_etl.py                      # ETL pipeline orchestrator
│
├── 📊 etl/                            # Data pipeline modules
│   ├── extraction.py                  # Multi-source data extraction
│   ├── transformation.py              # Data cleaning & validation
│   ├── loading.py                     # Database persistence
│   ├── news_etl.py                    # News & sentiment pipeline
│   ├── financials_etl.py              # Financial reports pipeline
│   └── earnings_etl.py                # Earnings data pipeline
│
├── 🗄️  models/                        # Data models & database
│   └── db_models.py                   # SQLAlchemy ORM models
│
├── 🔧 services/                       # Service layer (REFACTORING)
│   ├── 🆕 base_service.py             # New: Base service pattern
│   ├── 🆕 service_adapter.py          # New: Migration adapter
│   ├── 🆕 refactored_financials.py    # New: Financials service
│   ├── 🆕 refactored_earnings.py      # New: Earnings service
│   ├── 🔄 financials.py               # Legacy: Being migrated
│   ├── 🔄 earnings.py                 # Legacy: Being migrated  
│   ├── 🔄 news.py                     # Legacy: Migration pending
│   ├── 🌐 alternative_financials.py   # Yahoo Finance integration
│   └── 💾 hardcoded_financials.py     # Fallback data source
│
├── 🎨 views/                          # Web interface
│   ├── dashboard.py                   # Main dashboard & charts
│   └── news.py                        # News sentiment views
│
├── 🛠️  utils/                         # Utility modules
│   ├── constants.py                   # Application constants
│   ├── cache.py                       # Intelligent caching system
│   ├── setup_nltk.py                  # NLTK configuration
│   └── logging_config.py              # Logging setup
│
├── 🧪 tests/                          # Test suite
│   ├── unit/                          # Unit tests
│   ├── integration/                   # Integration tests
│   └── test_*.py                      # Test modules
│
├── 🎨 static/                         # CSS, JS, images
├── 📄 templates/                      # Jinja2 HTML templates
└── 📚 documentation/                  # Project documentation
```

### 🔄 **Service Architecture (During Migration)**

| Layer | Purpose | Status |
|-------|---------|--------|
| **Service Adapters** | Seamless old/new service integration | ✅ Production Ready |
| **BaseDataService** | Common patterns for new services | ✅ Foundation Complete |
| **Refactored Services** | New modular service implementations | 🔄 In Progress |
| **Legacy Services** | Original services (backward compatible) | 🔄 Being Phased Out |

---

## 🎯 **Supported Stocks**

Currently tracking **coffee and beverage industry leaders**:

| Symbol | Company | Market Cap | Data Sources |
|--------|---------|------------|--------------|
| **SBUX** | Starbucks Corporation | Large Cap | Finnhub + Yahoo + Hardcoded |
| **KDP** | Keurig Dr Pepper | Large Cap | Finnhub + Yahoo |
| **BROS** | Dutch Bros Inc. | Mid Cap | Yahoo + Hardcoded |
| **FARM** | Farmer Bros. Co. | Small Cap | Hardcoded + Manual |

*Easy to extend - add new symbols to `coffee_stocks` list in `views/dashboard.py`*

---

## 🧑‍💻 **Development Guide**

### **🚧 Working During Refactoring**

**Important Guidelines:**
1. **Use service adapters** for data access (handles both architectures)
2. **New features** should implement `BaseDataService` pattern
3. **Avoid modifying legacy services** (scheduled for removal)
4. **Some tests temporarily disabled** during migration

### **Adding New Stocks**
```python
# In views/dashboard.py
coffee_stocks = ["SBUX", "KDP", "BROS", "FARM", "YOUR_SYMBOL"]
```

### **Creating New Services (Recommended Pattern)**
```python
from services.base_service import BaseDataService

class MyDataService(BaseDataService):
    model_class = MyModel
    data_type = "my_data"
    cache_ttl = 3600
    
    @classmethod
    def _query_database(cls, session, symbol, **kwargs):
        # Database query implementation
        return session.query(cls.model_class).filter_by(symbol=symbol).all()
    
    @classmethod
    def _run_etl_pipeline(cls, symbol):
        # ETL trigger implementation
        run_my_etl_pipeline(symbol)
    
    @classmethod
    def _try_alternative_sources(cls, symbol, **kwargs):
        # Fallback data sources
        return fetch_alternative_data(symbol)
```

### **Running ETL for Specific Stocks**
```bash
flask run-etl --symbol=SBUX    # Single stock
flask run-etl                  # All stocks
```

---

## 🚀 **Production Deployment**

### **Environment Setup**
```bash
# Production database
export DATABASE_URL=postgresql://user:pass@prod-host:5432/finance_db

# API keys
export FINNHUB_API_KEY=your_production_key
export ALPHA_VANTAGE_API_KEY=your_production_key

# Optional: Redis for distributed caching
export REDIS_URL=redis://localhost:6379
```

### **Gunicorn Deployment**
```bash
gunicorn --workers=4 --bind=0.0.0.0:8000 --timeout=120 app:app
```

### **Docker Deployment**
```bash
docker build -t finance-integration .
docker run -p 8000:5000 --env-file .env finance-integration
```

---

## 📊 **Performance & Monitoring**

### **Built-in Optimizations**
- ⚡ **Intelligent caching** with adaptive TTL
- 🔄 **Background data refresh** prevents user wait times  
- 📉 **Data downsampling** for large datasets
- 🧵 **Thread-safe operations** with connection pooling
- ⏱️ **Request timeouts** prevent hanging operations

### **Monitoring Endpoints**
- `/cache-control` - Cache statistics and management
- Health checks built into service adapters
- Comprehensive logging with structured output

---

## 🤝 **Contributing**

We welcome contributions! Please see our development guidelines:

1. **Fork the repository**
2. **Create feature branch** (`git checkout -b feature/amazing-feature`)
3. **Follow the new service patterns** (BaseDataService)
4. **Add tests** for new functionality
5. **Submit pull request**

### **Code Quality Standards**
- **Black** for code formatting
- **Flake8** for linting  
- **Pytest** for testing
- **Type hints** encouraged

---

## 📚 **Documentation**

- [Yahoo Finance Integration Guide](documentation/yahoo_finance_integration.md)
- [Service Migration Guide](documentation/service_migration.md) *(Coming Soon)*
- [API Reference](documentation/api_reference.md) *(Coming Soon)*

---

## 📜 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 **Acknowledgments**

- **Finnhub** for comprehensive financial data API
- **Yahoo Finance** for reliable backup data source
- **Plotly** for beautiful interactive visualizations
- **Flask** ecosystem for robust web framework
- **NLTK** for sentiment analysis capabilities

---

<div align="center">

**⭐ Star this repo if you find it useful! ⭐**

[Report Bug](https://github.com/mseijse01/finance-integration/issues) • [Request Feature](https://github.com/mseijse01/finance-integration/issues) • [Documentation](documentation/)

</div>
