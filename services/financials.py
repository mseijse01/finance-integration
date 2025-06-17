"""
Refactored Financials Service using Base Service pattern
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import requests
from sqlalchemy import desc
from sqlalchemy.orm import Session

from config import Config
from etl.financials_etl import run_financials_etl_pipeline
from models.db_models import FinancialReport
from services.alternative_financials import fetch_yahoo_financials
from services.base_service import BaseDataService
from services.hardcoded_financials import get_hardcoded_financials
from utils.cache import adaptive_ttl_cache, rate_limited_api
from utils.logging_config import logger


class FinancialsService(BaseDataService):
    """Service for fetching financial data"""

    model_class = FinancialReport
    data_type = "financials"
    cache_ttl = 3600 * 6  # 6 hours
    cache_max_ttl = 3600 * 12  # 12 hours
    etl_timeout = 20  # seconds

    @classmethod
    @adaptive_ttl_cache(base_ttl=3600 * 6, max_ttl=3600 * 12, error_ttl=300)
    def fetch_financials(cls, symbol: str, freq: str = "quarterly") -> Dict[str, Any]:
        """
        Public API to fetch financials for a given stock symbol.
        Uses the base service pattern with specific handling for financial data.
        """
        from models.db_models import SessionLocal

        session = SessionLocal()
        try:
            return cls.fetch_data(session, symbol, freq=freq)
        finally:
            session.close()

    @classmethod
    def _query_database(
        cls, session: Session, symbol: str, **kwargs
    ) -> List[FinancialReport]:
        """Query financial reports from the database"""
        freq = kwargs.get("freq", "quarterly")
        report_type = "quarterly" if freq == "quarterly" else "annual"

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

    @classmethod
    def _format_records(
        cls, records: List[FinancialReport], source: str = "database"
    ) -> Dict[str, Any]:
        """Format financial records for the API response"""
        data = []
        for record in records:
            financial_data = {
                "year": record.year,
                "quarter": record.quarter,
                "report": record.report_data,
                "filing_date": record.filing_date.strftime("%Y-%m-%d")
                if record.filing_date
                else None,
            }
            data.append(financial_data)
        return {"data": data, "source": source}

    @classmethod
    def _run_etl_pipeline(cls, symbol: str) -> None:
        """Run the financials ETL pipeline"""
        run_financials_etl_pipeline(symbol)

    @classmethod
    def _try_alternative_sources(cls, symbol: str, **kwargs) -> Dict[str, Any]:
        """Try alternative data sources for financials"""
        freq = kwargs.get("freq", "quarterly")
        report_type = "quarterly" if freq == "quarterly" else "annual"

        # Try Yahoo Finance first
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
            return cls.fetch_financials(symbol, "annual")

        # Try hardcoded data as a last resort
        logger.info(
            f"No financials found in any standard source for {symbol}, trying hardcoded data"
        )
        hardcoded_financials = get_hardcoded_financials(symbol, report_type)

        if hardcoded_financials and len(hardcoded_financials.get("data", [])) > 0:
            logger.info(f"Using hardcoded financial data for {symbol}")
            return hardcoded_financials

        # Fallback to API as absolute last resort
        logger.warning(
            f"No financials found for {symbol} in any source, including hardcoded data"
        )
        return cls._legacy_fetch_financials(symbol, freq)

    @classmethod
    @rate_limited_api(calls_per_minute=10)
    def _legacy_fetch_financials(
        cls, symbol: str, freq: str = "quarterly"
    ) -> Dict[str, Any]:
        """Legacy method that directly calls the API."""
        url = "https://finnhub.io/api/v1/stock/financials-reported"
        params = {
            "symbol": symbol,
            "token": Config.FINNHUB_API_KEY,
            "freq": freq,
        }

        try:
            logger.info(f"[LEGACY] Fetching {freq} financials for {symbol} via API")
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if (
                isinstance(data, dict)
                and "data" in data
                and isinstance(data["data"], list)
            ):
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
            logger.error(
                f"[LEGACY] Error fetching financials for {symbol}", exc_info=True
            )
            return {"data": [], "error": str(e)}
