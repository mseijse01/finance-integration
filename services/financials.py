import requests
from config import Config
from utils.logging_config import logger
from utils.cache import timed_cache
from models.db_models import SessionLocal, FinancialReport
from sqlalchemy import desc
from datetime import datetime, timedelta
from etl.financials_etl import run_financials_etl_pipeline


@timed_cache(expire_seconds=3600 * 12)  # Cache for 12 hours - financials rarely change
def fetch_financials(symbol: str, freq: str = "quarterly"):
    """
    Fetches financials for a given stock symbol from the database.
    Falls back to ETL pipeline if no data is found.
    """
    session = SessionLocal()
    try:
        # Map frequency parameter to report_type in database
        report_type = "quarterly" if freq == "quarterly" else "annual"

        # Check if we have any recent financial data
        recent_date = datetime.now() - timedelta(
            days=30
        )  # Financial data is considered stale after 30 days

        recent_financials = (
            session.query(FinancialReport)
            .filter(
                FinancialReport.symbol == symbol,
                FinancialReport.report_type == report_type,
                FinancialReport.fetched_at >= recent_date,
            )
            .first()
        )

        # If no recent financials, trigger the ETL pipeline to fetch fresh data
        if not recent_financials:
            logger.info(
                f"No recent {report_type} financials found for {symbol}, triggering ETL pipeline"
            )
            run_financials_etl_pipeline(symbol)

        # Query the database for financial reports
        financial_records = (
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

        # Convert to the format expected by the dashboard
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

        logger.info(
            f"Fetched {len(data)} {report_type} financial reports for {symbol} from database"
        )
        if data:
            return {"data": data}
        elif freq == "quarterly":
            # Fallback to annual if quarterly not found
            logger.info(f"No quarterly financials found for {symbol}, trying annual")
            return fetch_financials(symbol, "annual")
        else:
            # Fallback to API if both quarterly and annual not found
            return _legacy_fetch_financials(symbol, freq)
    except Exception as e:
        logger.error(
            f"Error fetching financials for {symbol} from database: {e}", exc_info=True
        )
        # Fallback to the original API call if database access fails
        return _legacy_fetch_financials(symbol, freq)
    finally:
        session.close()


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
        response = requests.get(url, params=params)
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

    except Exception as e:
        logger.error(f"[LEGACY] Error fetching financials for {symbol}", exc_info=True)
        return {"data": []}
