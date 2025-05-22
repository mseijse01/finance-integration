import requests
from config import Config
from utils.logging_config import logger
from utils.cache import timed_cache
from models.db_models import SessionLocal, Earnings
from sqlalchemy import desc
from datetime import datetime, timedelta
from etl.earnings_etl import run_earnings_etl_pipeline
from services.alternative_financials import fetch_yahoo_financials
from services.hardcoded_financials import get_hardcoded_earnings


@timed_cache(
    expire_seconds=3600 * 24
)  # Cache for 24 hours - earnings reports are quarterly
def fetch_earnings(symbol: str):
    """
    Fetches earnings data for a given stock symbol from the database.
    Falls back to ETL pipeline if no data is found.
    If ETL pipeline doesn't find data, tries Yahoo Finance as alternative source.
    If Yahoo Finance doesn't have data, tries hardcoded data as a last resort.
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
            # Add source information
            for earning in earnings:
                earning["source"] = "finnhub"
            return earnings
        else:
            # Try Yahoo Finance as an alternative data source
            logger.info(
                f"No earnings found in database for {symbol}, trying Yahoo Finance"
            )
            yahoo_data = fetch_yahoo_financials(symbol)

            if yahoo_data["quarterly_earnings"]:
                logger.info(
                    f"Retrieved quarterly earnings from Yahoo Finance for {symbol}"
                )
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
