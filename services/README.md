# Service Adapters

This directory contains service adapters that act as intermediaries between the application and the data sources.

## Architecture Overview

The finance application now uses a three-layered architecture for data access:

1. **ETL Pipelines** (Primary): Responsible for extracting, transforming, and loading data into the database
2. **Service Adapters** (This folder): Smart adapters that determine the best way to fetch data
3. **Direct API Access** (Fallback): Used only when database access fails

## Service Adapter Pattern

Each service file follows a common pattern:

1. First attempt to get data from the database
2. If data is stale or missing, trigger the corresponding ETL pipeline to refresh
3. If database access fails, fall back to direct API calls as a last resort

This approach provides:
- **Performance**: Most requests are served from the database
- **Freshness**: Stale data is automatically refreshed
- **Reliability**: Multiple fallback mechanisms
- **Backward Compatibility**: Legacy code still works

## Available Services

- `news.py`: Company news articles with sentiment analysis
- `financials.py`: Financial reports (quarterly and annual)
- `earnings.py`: Earnings reports

## Usage Example

```python
from services.news import fetch_company_news

# The adapter handles all the complexity behind the scenes
news = fetch_company_news("AAPL", days=30)
```

## Relationship with ETL Pipeline

These service adapters complement the ETL pipeline rather than replacing it:

- ETL pipeline runs on a schedule or on demand to maintain the database
- Service adapters provide a smoother transition and safety net
- This dual approach ensures data is always available, even if one mechanism fails 