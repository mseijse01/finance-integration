from datetime import datetime

import requests

from config import Config
from models.db_models import Earnings, SessionLocal
from utils.logging_config import logger


def extract_earnings(symbol: str):
    """
    Extract earnings data for a given stock symbol from Finnhub.
    """
    url = "https://finnhub.io/api/v1/stock/earnings"
    params = {
        "symbol": symbol,
        "token": Config.FINNHUB_API_KEY,
    }

    try:
        logger.info(f"[Earnings ETL] Extracting earnings for {symbol}")
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if isinstance(data, list):
            logger.info(
                f"[Earnings ETL] Extracted {len(data)} earnings records for {symbol}"
            )
            return data
        else:
            logger.warning(
                f"[Earnings ETL] Unexpected earnings format for {symbol}: {type(data)}"
            )
            return []

    except Exception as e:
        logger.error(
            f"[Earnings ETL] Error extracting earnings for {symbol}: {e}", exc_info=True
        )
        return []


def transform_earnings(earnings_data, symbol):
    """
    Transform earnings data by normalizing structure and adding derived fields.
    """
    try:
        logger.info(
            f"[Earnings ETL] Transforming {len(earnings_data)} earnings records for {symbol}"
        )

        transformed_earnings = []

        for earning in earnings_data:
            # Parse period date
            period_str = earning.get("period", "")
            period_date = None
            quarter = None
            year = None

            try:
                if period_str:
                    period_date = datetime.strptime(period_str, "%Y-%m-%d")
                    # Calculate quarter from month
                    month = period_date.month
                    quarter = (month - 1) // 3 + 1
                    year = period_date.year
            except Exception as e:
                logger.warning(
                    f"[Earnings ETL] Could not parse period date: {period_str}",
                    exc_info=True,
                )

            # Get actual and estimated EPS
            eps_actual = earning.get("actual")
            eps_estimate = earning.get("estimate")

            # Calculate surprise and surprise percent if both values are present
            eps_surprise = None
            eps_surprise_percent = None
            is_beat = None

            if eps_actual is not None and eps_estimate is not None:
                try:
                    eps_actual = float(eps_actual)
                    eps_estimate = float(eps_estimate)
                    eps_surprise = eps_actual - eps_estimate
                    # Avoid division by zero
                    if eps_estimate != 0:
                        eps_surprise_percent = (eps_surprise / abs(eps_estimate)) * 100
                    is_beat = eps_actual > eps_estimate
                except (ValueError, TypeError):
                    pass

            # Create normalized earnings record
            transformed_earning = {
                "symbol": symbol,
                "period": period_date,
                "quarter": quarter,
                "year": year,
                "eps_actual": eps_actual,
                "eps_estimate": eps_estimate,
                "eps_surprise": eps_surprise,
                "eps_surprise_percent": eps_surprise_percent,
                "revenue_actual": earning.get("revenueActual"),
                "revenue_estimate": earning.get("revenueEstimate"),
                "revenue_surprise": None,  # Will calculate if both are present
                "revenue_surprise_percent": None,
                "is_beat": is_beat,
            }

            # Calculate revenue surprise if both values are present
            revenue_actual = transformed_earning["revenue_actual"]
            revenue_estimate = transformed_earning["revenue_estimate"]

            if revenue_actual is not None and revenue_estimate is not None:
                try:
                    revenue_actual = float(revenue_actual)
                    revenue_estimate = float(revenue_estimate)
                    transformed_earning["revenue_surprise"] = (
                        revenue_actual - revenue_estimate
                    )
                    # Avoid division by zero
                    if revenue_estimate != 0:
                        transformed_earning["revenue_surprise_percent"] = (
                            (revenue_actual - revenue_estimate) / abs(revenue_estimate)
                        ) * 100
                    # Update is_beat if not already set by EPS
                    if transformed_earning["is_beat"] is None:
                        transformed_earning["is_beat"] = (
                            revenue_actual > revenue_estimate
                        )
                except (ValueError, TypeError):
                    pass

            transformed_earnings.append(transformed_earning)

        logger.info(
            f"[Earnings ETL] Transformed {len(transformed_earnings)} earnings records for {symbol}"
        )
        return transformed_earnings

    except Exception as e:
        logger.error(
            f"[Earnings ETL] Error transforming earnings for {symbol}: {e}",
            exc_info=True,
        )
        return []


def load_earnings_to_db(transformed_earnings):
    """
    Load transformed earnings data into the database.
    """
    session = SessionLocal()
    try:
        logger.info(
            f"[Earnings ETL] Loading {len(transformed_earnings)} earnings records to database"
        )

        # For each earnings record, create or update the database record
        for earning_data in transformed_earnings:
            # Skip records without a valid period
            if not earning_data["period"]:
                continue

            # Check if the earnings record already exists
            existing = (
                session.query(Earnings)
                .filter_by(symbol=earning_data["symbol"], period=earning_data["period"])
                .first()
            )

            if existing:
                # Update existing record
                for key, value in earning_data.items():
                    setattr(existing, key, value)
            else:
                # Create new record
                earnings = Earnings(**earning_data)
                session.add(earnings)

        session.commit()
        logger.info("[Earnings ETL] Earnings data loaded successfully")
    except Exception as e:
        session.rollback()
        logger.error(f"[Earnings ETL] Error loading earnings data: {e}", exc_info=True)
    finally:
        session.close()


def run_earnings_etl_pipeline(symbol):
    """
    Run the full ETL pipeline for earnings data.
    """
    try:
        logger.info(f"[Earnings ETL] Starting earnings ETL pipeline for {symbol}")
        raw_earnings = extract_earnings(symbol)
        if raw_earnings:
            transformed_earnings = transform_earnings(raw_earnings, symbol)
            if transformed_earnings:
                load_earnings_to_db(transformed_earnings)
        logger.info(f"[Earnings ETL] Earnings ETL pipeline completed for {symbol}")
        return True
    except Exception as e:
        logger.error(
            f"[Earnings ETL] Earnings ETL pipeline failed for {symbol}: {e}",
            exc_info=True,
        )
        return False
