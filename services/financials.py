import requests
import concurrent.futures
from config import Config
from utils.logging_config import logger
from utils.cache import adaptive_ttl_cache, rate_limited_api
from models.db_models import SessionLocal, FinancialReport
from sqlalchemy import desc
from datetime import datetime, timedelta
import threading
from etl.financials_etl import run_financials_etl_pipeline
from services.alternative_financials import fetch_yahoo_financials
from services.hardcoded_financials import get_hardcoded_financials


# Global thread pool for parallel ETL operations
ETL_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=4)
ETL_TIMEOUT = 20  # seconds

# Thread-local storage for ETL operations in progress
_etl_operations = threading.local()


@adaptive_ttl_cache(
    base_ttl=3600 * 6, max_ttl=3600 * 12, error_ttl=300
)  # 6 hours cache, errors for 5 minutes
def fetch_financials(symbol: str, freq: str = "quarterly"):
    """
    Fetches financials for a given stock symbol from the database.
    Falls back to ETL pipeline if no data is found.
    If ETL pipeline doesn't find data, tries Yahoo Finance as alternative source.
    If Yahoo Finance doesn't have data, tries hardcoded data as a last resort.
    """
    session = SessionLocal()
    try:
        # Map frequency parameter to report_type in database
        report_type = "quarterly" if freq == "quarterly" else "annual"

        # Fast path - check if we have data in the database first
        financial_records = _query_database_for_financials(session, symbol, report_type)

        # If we have data, return it immediately
        if financial_records:
            logger.info(
                f"Fetched {len(financial_records)} {report_type} financial reports for {symbol} from database"
            )
            return {
                "data": _format_financial_records(financial_records),
                "source": "finnhub",
            }

        # No data in database - need to find a source
        logger.info(
            f"No {report_type} financials found in database for {symbol}, trying alternatives"
        )

        # Check if ETL is already running for this symbol
        is_etl_running = getattr(_etl_operations, f"{symbol}_etl_running", False)

        if not is_etl_running:
            # Mark ETL as running
            setattr(_etl_operations, f"{symbol}_etl_running", True)
            try:
                # Try running ETL pipeline with a timeout
                logger.info(
                    f"Triggering ETL pipeline for {symbol} financials with {ETL_TIMEOUT}s timeout"
                )
                future = ETL_EXECUTOR.submit(run_financials_etl_pipeline, symbol)
                future.result(
                    timeout=ETL_TIMEOUT
                )  # Wait for ETL to complete with timeout

                # Check if ETL produced data
                financial_records = _query_database_for_financials(
                    session, symbol, report_type
                )
                if financial_records:
                    logger.info(
                        f"ETL pipeline successfully fetched financials for {symbol}"
                    )
                    return {
                        "data": _format_financial_records(financial_records),
                        "source": "finnhub",
                    }
            except concurrent.futures.TimeoutError:
                logger.warning(
                    f"ETL pipeline timed out after {ETL_TIMEOUT}s for {symbol}"
                )
            except Exception as e:
                logger.error(f"Error in ETL pipeline for {symbol}: {e}")
            finally:
                # Reset ETL running flag
                setattr(_etl_operations, f"{symbol}_etl_running", False)
        else:
            logger.info(f"ETL already running for {symbol}, skipping")

        # Try Yahoo Finance as an alternative data source
        logger.info(
            f"No financials found in database for {symbol}, trying Yahoo Finance"
        )
        yahoo_data = fetch_yahoo_financials(symbol)

        # Check if we got actual financial data from Yahoo
        yahoo_financials = None
        if (
            report_type == "quarterly"
            and yahoo_data.get("quarterly_financials")
            and yahoo_data["quarterly_financials"].get("data")
        ):
            yahoo_financials = yahoo_data["quarterly_financials"]
            logger.info(
                f"Retrieved quarterly financials from Yahoo Finance for {symbol}"
            )
        elif (
            report_type == "annual"
            and yahoo_data.get("annual_financials")
            and yahoo_data["annual_financials"].get("data")
        ):
            yahoo_financials = yahoo_data["annual_financials"]
            logger.info(f"Retrieved annual financials from Yahoo Finance for {symbol}")

        if yahoo_financials and len(yahoo_financials.get("data", [])) > 0:
            yahoo_financials["source"] = "yahoo_finance"
            return yahoo_financials

        # If quarterly not found, try annual
        elif freq == "quarterly":
            logger.info(f"No quarterly financials found for {symbol}, trying annual")
            return fetch_financials(symbol, "annual")
        else:
            # Try hardcoded data as a last resort
            logger.info(
                f"No financials found in any standard source for {symbol}, trying hardcoded data"
            )
            hardcoded_financials = get_hardcoded_financials(symbol, report_type)

            if (
                hardcoded_financials
                and hardcoded_financials.get("data")
                and len(hardcoded_financials["data"]) > 0
            ):
                logger.info(f"Using hardcoded financial data for {symbol}")
                return hardcoded_financials

            # Fallback to API as absolute last resort
            logger.warning(
                f"No financials found for {symbol} in any source, including hardcoded data"
            )
            return _legacy_fetch_financials(symbol, freq)
    except Exception as e:
        logger.error(
            f"Error fetching financials for {symbol} from database: {e}", exc_info=True
        )
        # Fallback to the original API call if database access fails
        return _legacy_fetch_financials(symbol, freq)
    finally:
        session.close()


def _query_database_for_financials(session, symbol, report_type):
    """Helper function to query database for financial records"""
    # Check if we have any recent financial data
    recent_date = datetime.now() - timedelta(
        days=30
    )  # Financial data is considered stale after 30 days

    # Query the database for financial reports
    return (
        session.query(FinancialReport)
        .filter(
            FinancialReport.symbol == symbol,
            FinancialReport.report_type == report_type,
        )
        .order_by(
            desc(FinancialReport.year),
            desc(FinancialReport.quarter)
            if report_type == "quarterly"
            else desc(FinancialReport.year),
        )
        .limit(4)
        .all()
    )


def _format_financial_records(financial_records):
    """Helper function to format financial records for the dashboard"""
    data = []
    for record in financial_records:
        financial_data = {
            "year": record.year,
            "quarter": record.quarter,
            "report": record.report_data,
            "filing_date": record.filing_date.strftime("%Y-%m-%d")
            if record.filing_date
            else None,
        }
        data.append(financial_data)
    return data


@rate_limited_api(calls_per_minute=10)  # Rate limit the legacy API calls
def _legacy_fetch_financials(symbol: str, freq: str = "quarterly"):
    """
    Legacy method that directly calls the API.
    Used as fallback if database access fails.
    """
    url = "https://finnhub.io/api/v1/stock/financials-reported"
    params = {
        "symbol": symbol,
        "token": Config.FINNHUB_API_KEY,
        "freq": freq,
    }

    try:
        logger.info(f"[LEGACY] Fetching {freq} financials for {symbol} via API")
        response = requests.get(url, params=params, timeout=10)  # Add timeout
        response.raise_for_status()
        data = response.json()

        if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
            logger.info(
                f"[LEGACY] Financials received for {symbol}: {len(data['data'])} records"
            )
            return data  # expected structure
        elif isinstance(data, list):  # fallback case
            logger.warning(
                f"[LEGACY] Unexpected format: financials returned as list for {symbol}"
            )
            return {"data": data}
        else:
            logger.warning(
                f"[LEGACY] Unexpected financials format for {symbol}: {type(data)}"
            )
            return {"data": []}

    except requests.exceptions.Timeout:
        logger.error(f"[LEGACY] Timeout fetching financials for {symbol}")
        return {"data": [], "error": "API timeout"}
    except Exception as e:
        logger.error(f"[LEGACY] Error fetching financials for {symbol}", exc_info=True)
        return {"data": [], "error": str(e)}
