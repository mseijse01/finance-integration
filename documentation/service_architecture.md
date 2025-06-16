# Service Architecture Documentation

## Overview

The Finance Integration Dashboard implements a sophisticated service architecture built around the **BaseDataService pattern**. This architecture provides intelligent data fetching with multiple fallback mechanisms, advanced caching strategies, and graceful error handling.

## Architecture Pattern

### BaseDataService Pattern

The `BaseDataService` class provides a generic framework for all data services in the application. It implements a consistent data fetching strategy that prioritizes performance and reliability.

**Core Philosophy:**
1. **Database First** - Always check cache before external APIs
2. **ETL on Demand** - Trigger data pipeline when cache is stale
3. **Intelligent Fallbacks** - Multiple backup data sources  
4. **Graceful Degradation** - Never leave users without data

### Service Hierarchy

```
BaseDataService (Abstract)
├── FinancialsService
├── EarningsService  
└── NewsService
```

Each service inherits the common data fetching logic while implementing domain-specific:
- Database queries
- Data formatting
- ETL pipeline integration
- Alternative data sources

## Data Flow Architecture

### 5-Layer Fallback System

```
1. Database Cache ──────────► Return cached data (fastest)
   │
   ▼ (if empty/stale)
2. ETL Pipeline Trigger ────► Fetch fresh data, store in DB
   │
   ▼ (if ETL fails)  
3. Alternative APIs ────────► Yahoo Finance, etc.
   │
   ▼ (if alternatives fail)
4. Hardcoded Data ──────────► Manually curated fallbacks
   │
   ▼ (absolute last resort)
5. Legacy Direct API ───────► Direct API calls with rate limiting
```

### Intelligent ETL Triggering

The service layer includes smart ETL management:

- **Thread Pool Execution**: ETL operations run in background threads
- **Timeout Protection**: ETL calls have configurable timeouts
- **Duplicate Prevention**: Prevents multiple ETL runs for same symbol
- **Thread-local Storage**: Tracks ETL operations in progress

## Service Implementation Details

### FinancialsService

**Purpose**: Fetch quarterly and annual financial reports

**Data Sources**:
1. Database (FinancialReport table)
2. Finnhub API via ETL pipeline
3. Yahoo Finance API 
4. Hardcoded financial data
5. Legacy Finnhub API direct calls

**Key Features**:
- Automatic quarterly→annual fallback
- Financial metric extraction and standardization
- Source attribution in responses

### EarningsService

**Purpose**: Fetch earnings reports and EPS data

**Data Sources**:
1. Database (Earnings table)
2. Finnhub API via ETL pipeline
3. Yahoo Finance earnings data
4. Hardcoded earnings data
5. Legacy Finnhub API direct calls

**Key Features**:
- EPS surprise calculation
- Beat/miss determination
- Historical earnings trend analysis

### NewsService

**Purpose**: Fetch company news with sentiment analysis

**Data Sources**:
1. Database (NewsArticle table)
2. Finnhub API via ETL pipeline
3. Legacy Finnhub API direct calls

**Key Features**:
- NLTK VADER sentiment analysis
- News categorization
- Real-time sentiment scoring

## Alternative Data Sources

### Yahoo Finance Integration

**Purpose**: Secondary data source for comprehensive financial coverage

**Implementation**: `services/alternative_financials.py`

**Key Functions**:
- `fetch_yahoo_financials`: Main Yahoo Finance data entry point
- `process_financials`: Transforms Yahoo DataFrames to internal format
- `process_earnings`: Handles Yahoo Finance earnings data
- `compare_financial_sources`: Cross-validates data between sources

**Data Transformation**:
- Yahoo Finance returns pandas DataFrames (metrics as rows, dates as columns)
- Extracts key metrics (revenue, net income) and reformats
- Adds source attribution and consistent date formatting
- Handles missing earnings data gracefully

**UI Integration**:
- Data source attribution displayed in dashboard
- Comparison view when multiple sources available
- Significant differences (>5%) highlighted for user awareness
- Special handling for stocks with known data issues

### Hardcoded Data Fallbacks

**Purpose**: Manually curated data for stocks with poor API coverage

**Implementation**: `services/hardcoded_financials.py`

**Key Functions**:
- `get_hardcoded_financials`: Curated financial data for specific stocks
- `get_hardcoded_earnings`: Curated earnings data for specific stocks

**Data Sources**: Manual curation from investor relations sites and SEC filings

## Service Adapter Pattern

### Migration Strategy

The application uses service adapters to provide seamless migration from legacy services to the new BaseDataService pattern:

**File**: `services/service_adapter.py`

**Features**:
- **Feature Toggle**: `USE_REFACTORED_SERVICES` flag
- **Automatic Fallback**: New service fails → old service
- **Backward Compatibility**: Existing view code unchanged
- **Gradual Migration**: Services can be migrated individually

### Adapter Implementation

```python
fetch_financials = with_fallback(
    old_fetch_financials, 
    FinancialsService.fetch_financials
)
```

The adapter tries the new service first, falling back to the legacy implementation if errors occur.

## Caching Architecture

### Multi-Level Caching

1. **Adaptive TTL Cache**: Base TTL with max TTL limits
2. **Error TTL**: Short cache duration for error responses
3. **Rate Limited API**: Prevents API abuse
4. **Background Data Loading**: Preloads popular symbols

### Cache Configuration

**Service-Specific TTL**:
- **Financials**: 6 hours base, 12 hours max
- **Earnings**: 12 hours base, 24 hours max  
- **News**: 2 hours base, 6 hours max

### Background Loading

The dashboard implements proactive data loading:

```python
def load_stock_data_background():
    """Preload data for popular symbols"""
    coffee_stocks = ["SBUX", "KDP", "BROS", "FARM"]
    for symbol in coffee_stocks:
        # Warm up cache in background thread
```

## Error Handling & Resilience

### Comprehensive Error Management

1. **Timeout Handling**: All external calls have timeouts
2. **Rate Limit Management**: Built-in API rate limiting
3. **Graceful Degradation**: Multiple fallback data sources
4. **User-Friendly Messages**: Clear error communication
5. **Logging**: Detailed error tracking and debugging

### Service Reliability Features

- **Circuit Breaker Pattern**: Prevents cascade failures
- **Retry Logic**: Configurable retry strategies
- **Health Checks**: Service status monitoring
- **Fallback Data**: Always provide some data to users

## Performance Optimizations

### Database Optimization

- **Query Limits**: Restrict result sets to recent data
- **Indexed Queries**: Optimized database queries
- **Connection Pooling**: Efficient database connections
- **Data Downsampling**: Reduce chart data for performance

### API Optimization

- **Request Batching**: Minimize API calls
- **Parallel Processing**: Concurrent data fetching
- **Smart Caching**: Aggressive cache strategies
- **Rate Limiting**: Prevent API quota exhaustion

## Configuration Management

### Service Configuration

Each service can be configured independently:

```python
class FinancialsService(BaseDataService):
    cache_ttl = 3600 * 6      # 6 hours
    cache_max_ttl = 3600 * 12 # 12 hours  
    etl_timeout = 20          # seconds
```

### Feature Toggles

- **Service Migration**: Enable/disable new services
- **ETL Triggering**: Control automatic ETL execution
- **Alternative Sources**: Toggle fallback data sources
- **Background Loading**: Control cache warming

## Monitoring & Observability

### Logging Strategy

- **Structured Logging**: Consistent log format
- **Performance Metrics**: Timing and success rates
- **Error Tracking**: Detailed exception logging
- **Service Attribution**: Track data sources used

### Cache Monitoring

- **Cache Hit Rates**: Monitor cache effectiveness
- **TTL Analytics**: Track cache expiration patterns
- **Memory Usage**: Monitor cache memory consumption
- **Background Loading**: Track preload performance

## Testing Strategy

### Service Testing

The architecture includes comprehensive testing:

**File**: `tests/unit/test_refactored_services.py`

**Test Coverage**:
- Database query formatting
- Fallback mechanism behavior
- Error handling scenarios
- Cache integration
- Service adapter functionality

### Integration Testing

- End-to-end data flow testing
- API integration validation
- Database integration testing
- Error scenario simulation

## Future Architecture Enhancements

### Planned Improvements

1. **Microservice Decomposition**: Split services into independent microservices
2. **Event-Driven Architecture**: Implement pub/sub for data updates
3. **GraphQL API**: Unified API layer for frontend
4. **Service Mesh**: Advanced service communication
5. **Real-time Updates**: WebSocket integration for live data

### Performance Enhancements

1. **Redis Caching**: Distributed caching layer
2. **CDN Integration**: Static asset optimization
3. **Database Sharding**: Horizontal scaling strategies
4. **Connection Pooling**: Advanced database optimization

---

> **Note**: This architecture has evolved from a simple API-based approach to a sophisticated, resilient service layer that prioritizes user experience and system reliability. 