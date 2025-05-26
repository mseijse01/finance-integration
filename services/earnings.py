import concurrent.futures
import threading
from datetime import datetime, timedelta

import requests
from sqlalchemy import desc

from config import Config
from etl.earnings_etl import run_earnings_etl_pipeline
from models.db_models import Earnings, SessionLocal
from services.alternative_financials import fetch_yahoo_financials
from services.hardcoded_financials import get_hardcoded_earnings
from utils.cache import adaptive_ttl_cache, rate_limited_api
from utils.logging_config import logger

# Global thread pool for parallel ETL operations
ETL_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=4)
ETL_TIMEOUT = 15  # seconds

# Thread-local storage for ETL operations in progress
_etl_operations = threading.local()


@adaptive_ttl_cache(base_ttl=3600 * 12, max_ttl=3600 * 24, error_ttl=300)
def fetch_earnings(symbol: str):
    """
    Fetches earnings data for a given stock symbol from the database.
    Falls back to ETL pipeline if no data is found.
    If ETL pipeline doesn't find data, tries Yahoo Finance as alternative source.
    If Yahoo Finance doesn't have data, tries hardcoded data as a last resort.
    """
    session = SessionLocal()
    try:
        # Fast path - check if we have data in the database first
        earnings_records = _query_database_for_earnings(session, symbol)

        # If we have data, return it immediately
        if earnings_records:
            logger.info(
                f"Fetched {len(earnings_records)} earnings records for {symbol} from database"
            )
            return _format_earnings_records(earnings_records, source="finnhub")

        # No data in database - need to find a source
        logger.info(f"No earnings found in database for {symbol}, trying alternatives")

        # Check if ETL is already running for this symbol
        is_etl_running = getattr(
            _etl_operations, f"{symbol}_earnings_etl_running", False
        )

        if not is_etl_running:
            # Mark ETL as running
            setattr(_etl_operations, f"{symbol}_earnings_etl_running", True)
            try:
                # Try running ETL pipeline with a timeout
                logger.info(
                    f"Triggering earnings ETL pipeline for {symbol} with {ETL_TIMEOUT}s timeout"
                )
                future = ETL_EXECUTOR.submit(run_earnings_etl_pipeline, symbol)
                future.result(
                    timeout=ETL_TIMEOUT
                )  # Wait for ETL to complete with timeout

                # Check if ETL produced data
                earnings_records = _query_database_for_earnings(session, symbol)
                if earnings_records:
                    logger.info(
                        f"ETL pipeline successfully fetched earnings for {symbol}"
                    )
                    return _format_earnings_records(earnings_records, source="finnhub")
            except concurrent.futures.TimeoutError:
                logger.warning(
                    f"Earnings ETL pipeline timed out after {ETL_TIMEOUT}s for {symbol}"
                )
            except Exception as e:
                logger.error(f"Error in earnings ETL pipeline for {symbol}: {e}")
            finally:
                # Reset ETL running flag
                setattr(_etl_operations, f"{symbol}_earnings_etl_running", False)
        else:
            logger.info(f"Earnings ETL already running for {symbol}, skipping")

        # Try Yahoo Finance as an alternative data source
        logger.info(f"No earnings found in database for {symbol}, trying Yahoo Finance")
        yahoo_data = fetch_yahoo_financials(symbol)

        if yahoo_data["quarterly_earnings"]:
            logger.info(f"Retrieved quarterly earnings from Yahoo Finance for {symbol}")
            return yahoo_data["quarterly_earnings"]
        else:
            # Try hardcoded data as a last resort
            logger.info(
                f"No earnings found in standard sources for {symbol}, trying hardcoded data"
            )
            hardcoded_earnings = get_hardcoded_earnings(symbol)
            if hardcoded_earnings:
                logger.info(f"Using hardcoded earnings data for {symbol}")
                return hardcoded_earnings

            # Fallback to API if no data found in any source
            logger.warning(
                f"No earnings found for {symbol} in any data source, including hardcoded data"
            )
            return _legacy_fetch_earnings(symbol)
    except Exception as e:
        logger.error(
            f"Error fetching earnings for {symbol} from database: {e}", exc_info=True
        )
        # Fallback to the original API call if database access fails
        return _legacy_fetch_earnings(symbol)
    finally:
        session.close()


def _query_database_for_earnings(session, symbol):
    """Helper function to query database for earnings records"""
    # Query the database for earnings reports
    return (
        session.query(Earnings)
        .filter(Earnings.symbol == symbol)
        .order_by(desc(Earnings.period))
        .limit(4)
        .all()
    )


def _format_earnings_records(earnings_records, source="finnhub"):
    """Helper function to format earnings records for the dashboard"""
    earnings = []
    for record in earnings_records:
        earning_data = {
            "actual": record.eps_actual,
            "estimate": record.eps_estimate,
            "surprise": record.eps_surprise,
            "surprisePercent": record.eps_surprise_percent,
            "period": record.period.strftime("%Y-%m-%d") if record.period else None,
            "quarter": record.quarter,
            "year": record.year,
            "source": source,
        }
        earnings.append(earning_data)
    return earnings


@rate_limited_api(calls_per_minute=10)  # Rate limit the legacy API calls
def _legacy_fetch_earnings(symbol: str):
    """
    Legacy method that directly calls the API.
    Used as fallback if database access fails.
    """
    url = "https://finnhub.io/api/v1/stock/earnings"
    params = {
        "symbol": symbol,
        "token": Config.FINNHUB_API_KEY,
        "freq": "quarterly",  # <-- Ensure quarterly data
    }

    try:
        logger.info(f"[LEGACY] Fetching earnings for {symbol} via API")
        response = requests.get(url, params=params, timeout=10)  # Add timeout
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list):
            logger.info(f"[LEGACY] Earnings received for {symbol}: {len(data)} records")
            # Add source information
            for item in data:
                item["source"] = "finnhub_api"
            return data
        else:
            logger.warning(f"[LEGACY] Unexpected earnings format for {symbol}: {data}")
            return []
    except requests.exceptions.Timeout:
        logger.error(f"[LEGACY] Timeout fetching earnings for {symbol}")
        return []
    except Exception as e:
        logger.error(
            f"[LEGACY] Error fetching earnings for {symbol}: {e}", exc_info=True
        )
        return []
