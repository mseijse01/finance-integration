# Yahoo Finance Integration

## Overview

This document explains how we've integrated Yahoo Finance as a secondary data source to provide more comprehensive financial data for certain stocks like Starbucks (SBUX) that may not be well-covered by our primary data provider, Finnhub.

## Architecture

The Yahoo Finance integration follows our existing service adapter pattern:

1. **Primary Data Source**: Finnhub API (with ETL pipeline)
2. **Secondary Data Source**: Yahoo Finance API (via `yfinance` library)
3. **Tertiary Data Source**: Hardcoded data from investor relations sites
4. **Fallback**: Direct API calls to primary source

## Implementation Details

### Core Components

1. **Alternative Financials Service**:
   - Location: `services/alternative_financials.py`
   - Purpose: Fetches and processes Yahoo Finance data
   - Functions: 
     - `fetch_yahoo_financials`: Main entry point to get financial data from Yahoo Finance
     - `process_financials`: Transforms Yahoo Finance dataframes to match our data model
     - `process_earnings`: Transforms Yahoo Finance earnings data to match our data model
     - `compare_financial_sources`: Compares data between Finnhub and Yahoo Finance to identify discrepancies

2. **Hardcoded Financials Service**:
   - Location: `services/hardcoded_financials.py` 
   - Purpose: Provides hardcoded financial and earnings data for stocks not covered by other sources
   - Functions:
     - `get_hardcoded_financials`: Returns manually curated financial data for specific stocks
     - `get_hardcoded_earnings`: Returns manually curated earnings data for specific stocks

3. **Service Adapter Integration**:
   - Modified `services/financials.py` and `services/earnings.py` to use Yahoo Finance as a fallback when Finnhub data is unavailable
   - Added hardcoded data as a tertiary source when both APIs fail
   - Added proper error handling for cases where all sources lack data

4. **Dashboard View Enhancements**:
   - Updated `views/dashboard.py` to display data source information
   - Added special handling for stocks with known data availability issues
   - Implemented a comparison display for cases where both sources have data with significant discrepancies

### Data Transformation

The Yahoo Finance API returns data in a different format than Finnhub:

1. **Yahoo Finance**:
   - Financial data comes as pandas DataFrames with metrics as rows and dates as columns
   - Earnings data may be unavailable via the standard API

2. **Transformation Process**:
   - Extract key metrics (revenue, net income) from the dataframes
   - Structure the data to match our internal format used by Finnhub
   - Add metadata including source attribution
   - Format dates and periods consistently

## Error Handling

The integration handles several error scenarios:

1. **No Data Available**: For stocks where neither Finnhub nor Yahoo Finance have data, our hardcoded data is used with clear attribution
2. **API Rate Limits**: Both APIs have rate limits, which are managed through caching and graceful fallbacks
3. **Parse Errors**: The code handles various data format issues that may occur with either source
4. **Special Case Handling**: For specific symbols like SBUX with known issues, custom messages are shown

## Data Sources & Fallback Pattern

Our dashboard implements a multi-layer fallback pattern:

1. **Database First**: Always attempt to retrieve from database first
2. **ETL Pipeline**: If database has no data, trigger ETL to get fresh data
3. **Yahoo Finance**: If ETL finds no data, try Yahoo Finance API
4. **Hardcoded Data**: If Yahoo Finance has no data, use manually curated data
5. **Direct API**: As absolute last resort, try direct API call
6. **User Message**: If all fails, display a helpful message for the user

## Data Comparison

When both sources have data for the same period, a comparison is provided in the UI:

1. Significant differences (>5%) are highlighted
2. Users can see data from both sources side by side
3. Percentage differences are calculated and displayed

## Usage

This cascading data source approach is automatically used without user intervention when:

1. Primary data source returns no data
2. A data refresh is triggered but primary source finds no data
3. Database access fails and direct API calls are required

## Future Enhancements

Potential improvements to the data source integration:

1. **ETL Pipeline Integration**: Create a separate Yahoo Finance ETL pipeline to store this data in the database
2. **API Performance Optimization**: Add more aggressive caching for Yahoo Finance API to prevent rate limit issues
3. **Enhanced Comparison**: Expand the comparison feature to include more metrics beyond revenue and net income
4. **User Selection**: Allow users to manually select their preferred data source
5. **Additional Sources**: Integrate more financial data sources for even better coverage 
6. **Data Updates**: Regularly update the hardcoded data to ensure it remains current
7. **Automated Scraping**: Create a system to automatically scrape investor relations sites for companies with poor API coverage 