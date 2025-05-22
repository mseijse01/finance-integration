import requests
from config import Config
from utils.logging_config import logger
from utils.cache import timed_cache
from models.db_models import SessionLocal, Earnings
from sqlalchemy import desc
from datetime import datetime, timedelta
from etl.earnings_etl import run_earnings_etl_pipeline


@timed_cache(
    expire_seconds=3600 * 24
)  # Cache for 24 hours - earnings reports are quarterly
def fetch_earnings(symbol: str):
    """
    Fetches earnings data for a given stock symbol from the database.
    Falls back to ETL pipeline if no data is found.
    """
    session = SessionLocal()
    try:
        # Check if we have any recent earnings data
        recent_date = datetime.now() - timedelta(
            days=30
        )  # Earnings data is considered stale after 30 days

        recent_earnings = (
            session.query(Earnings)
            .filter(Earnings.symbol == symbol, Earnings.fetched_at >= recent_date)
            .first()
        )

        # If no recent earnings, trigger the ETL pipeline to fetch fresh data
        if not recent_earnings:
            logger.info(
                f"No recent earnings found for {symbol}, triggering ETL pipeline"
            )
            run_earnings_etl_pipeline(symbol)

        # Query the database for earnings reports
        earnings_records = (
            session.query(Earnings)
            .filter(Earnings.symbol == symbol)
            .order_by(desc(Earnings.period))
            .limit(4)
            .all()
        )

        # Convert to the format expected by the dashboard
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
            }
            earnings.append(earning_data)

        logger.info(
            f"Fetched {len(earnings)} earnings records for {symbol} from database"
        )
        if earnings:
            return earnings
        else:
            # Fallback to API if no earnings found in the database
            return _legacy_fetch_earnings(symbol)
    except Exception as e:
        logger.error(
            f"Error fetching earnings for {symbol} from database: {e}", exc_info=True
        )
        # Fallback to the original API call if database access fails
        return _legacy_fetch_earnings(symbol)
    finally:
        session.close()


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
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list):
            logger.info(f"[LEGACY] Earnings received for {symbol}: {len(data)} records")
        else:
            logger.warning(f"[LEGACY] Unexpected earnings format for {symbol}: {data}")
        return data
    except Exception as e:
        logger.error(
            f"[LEGACY] Error fetching earnings for {symbol}: {e}", exc_info=True
        )
        return []
