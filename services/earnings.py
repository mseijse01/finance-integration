"""
Refactored Earnings Service using Base Service pattern
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import requests
from sqlalchemy import desc
from sqlalchemy.orm import Session

from config import Config
from etl.earnings_etl import run_earnings_etl_pipeline
from models.db_models import Earnings
from services.alternative_financials import fetch_yahoo_financials
from services.base_service import BaseDataService
from services.hardcoded_financials import get_hardcoded_earnings
from utils.cache import adaptive_ttl_cache, rate_limited_api
from utils.logging_config import logger


class EarningsService(BaseDataService):
    """Service for fetching earnings data"""

    model_class = Earnings
    data_type = "earnings"
    cache_ttl = 3600 * 12  # 12 hours
    cache_max_ttl = 3600 * 24  # 24 hours
    etl_timeout = 15  # seconds

    @classmethod
    @adaptive_ttl_cache(base_ttl=3600 * 12, max_ttl=3600 * 24, error_ttl=300)
    def fetch_earnings(cls, symbol: str) -> List[Dict[str, Any]]:
        """
        Public API to fetch earnings for a given stock symbol.
        Uses the base service pattern with specific handling for earnings data.
        """
        from models.db_models import SessionLocal

        session = SessionLocal()
        try:
            result = cls.fetch_data(session, symbol)
            return result.get("data", [])
        finally:
            session.close()

    @classmethod
    def _query_database(cls, session: Session, symbol: str, **kwargs) -> List[Earnings]:
        """Query earnings from the database"""
        return (
            session.query(Earnings)
            .filter(Earnings.symbol == symbol)
            .order_by(desc(Earnings.year), desc(Earnings.quarter))
            .limit(8)  # Last 2 years of quarterly reports
            .all()
        )

    @classmethod
    def _format_records(
        cls, records: List[Earnings], source: str = "database"
    ) -> Dict[str, Any]:
        """Format earnings records for the API response"""
        data = []
        for record in records:
            earnings_data = {
                "period": record.period.strftime("%Y-%m-%d") if record.period else None,
                "year": record.year,
                "quarter": record.quarter,
                "eps_actual": record.eps_actual,
                "eps_estimate": record.eps_estimate,
                "eps_surprise": record.eps_surprise,
                "eps_surprise_percent": record.eps_surprise_percent,
                "revenue_actual": record.revenue_actual,
                "revenue_estimate": record.revenue_estimate,
                "source": source,
                "is_beat": record.is_beat,
            }
            data.append(earnings_data)
        return {"data": data, "source": source}

    @classmethod
    def _run_etl_pipeline(cls, symbol: str) -> None:
        """Run the earnings ETL pipeline"""
        run_earnings_etl_pipeline(symbol)

    @classmethod
    def _try_alternative_sources(cls, symbol: str, **kwargs) -> Dict[str, Any]:
        """Try alternative data sources for earnings"""
        logger.info(f"No earnings found in database for {symbol}, trying Yahoo Finance")

        # Try Yahoo Finance
        yahoo_data = fetch_yahoo_financials(symbol)

        # Check if Yahoo returned earnings data
        if (
            yahoo_data.get("quarterly_earnings")
            and len(yahoo_data["quarterly_earnings"]) > 0
        ):
            logger.info(f"Retrieved earnings from Yahoo Finance for {symbol}")
            earnings_data = []

            for item in yahoo_data["quarterly_earnings"]:
                earnings_item = {
                    "period": item.get("period", ""),
                    "year": item.get("year", 0),
                    "quarter": item.get("quarter", 0),
                    "eps_actual": item.get("actual", None),
                    "eps_estimate": item.get("estimate", None),
                    "source": "yahoo_finance",
                }

                # Calculate surprise if we have both actual and estimate
                if (
                    earnings_item["eps_actual"] is not None
                    and earnings_item["eps_estimate"] is not None
                ):
                    eps_actual = float(earnings_item["eps_actual"])
                    eps_estimate = float(earnings_item["eps_estimate"])
                    eps_surprise = eps_actual - eps_estimate

                    earnings_item["eps_surprise"] = eps_surprise
                    if eps_estimate != 0:
                        earnings_item["eps_surprise_percent"] = (
                            eps_surprise / abs(eps_estimate)
                        ) * 100
                    earnings_item["is_beat"] = eps_actual > eps_estimate

                earnings_data.append(earnings_item)

            return {"data": earnings_data, "source": "yahoo_finance"}

        # Try hardcoded data as a last resort
        logger.info(
            f"No earnings found in Yahoo Finance for {symbol}, trying hardcoded data"
        )
        hardcoded_earnings = get_hardcoded_earnings(symbol)

        if hardcoded_earnings and len(hardcoded_earnings) > 0:
            logger.info(f"Using hardcoded earnings data for {symbol}")
            return {"data": hardcoded_earnings, "source": "hardcoded"}

        # Fallback to API as absolute last resort
        logger.warning(
            f"No earnings found for {symbol} in any source, including hardcoded data"
        )
        return cls._legacy_fetch_earnings(symbol)

    @classmethod
    @rate_limited_api(calls_per_minute=10)
    def _legacy_fetch_earnings(cls, symbol: str) -> Dict[str, Any]:
        """Legacy method that directly calls the API."""
        url = "https://finnhub.io/api/v1/stock/earnings"
        params = {
            "symbol": symbol,
            "token": Config.FINNHUB_API_KEY,
        }

        try:
            logger.info(f"[LEGACY] Fetching earnings for {symbol} via API")
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if isinstance(data, list) and len(data) > 0:
                # Format the API response
                earnings_data = []

                for item in data:
                    earnings_item = {
                        "period": item.get("period", ""),
                        "year": int(item.get("period", "0000-00-00")[:4])
                        if item.get("period")
                        else 0,
                        "quarter": item.get("quarter", 0),
                        "eps_actual": item.get("actual", None),
                        "eps_estimate": item.get("estimate", None),
                        "eps_surprise": item.get("surprise", None),
                        "eps_surprise_percent": item.get("surprisePercent", None),
                        "source": "finnhub",
                        "is_beat": item.get("actual", 0) > item.get("estimate", 0)
                        if item.get("actual") is not None
                        and item.get("estimate") is not None
                        else None,
                    }
                    earnings_data.append(earnings_item)

                logger.info(
                    f"[LEGACY] Retrieved {len(earnings_data)} earnings records for {symbol}"
                )
                return {"data": earnings_data, "source": "finnhub"}
            else:
                logger.warning(
                    f"[LEGACY] Unexpected or empty earnings format for {symbol}"
                )
                return {"data": [], "error": "No earnings data available"}

        except requests.exceptions.Timeout:
            logger.error(f"[LEGACY] Timeout fetching earnings for {symbol}")
            return {"data": [], "error": "API timeout"}
        except Exception as e:
            logger.error(
                f"[LEGACY] Error fetching earnings for {symbol}", exc_info=True
            )
            return {"data": [], "error": str(e)}
