"""
Refactored News Service using Base Service pattern
"""

import ssl
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import nltk
import requests
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from sqlalchemy import desc
from sqlalchemy.orm import Session

from config import Config
from etl.news_etl import run_news_etl_pipeline
from models.db_models import NewsArticle
from services.base_service import BaseDataService
from utils.cache import adaptive_ttl_cache, rate_limited_api
from utils.logging_config import logger

# Fix SSL certificate issues for NLTK downloads
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# Ensure the lexicon is available
nltk.download("vader_lexicon", quiet=True)
sia = SentimentIntensityAnalyzer()


class NewsService(BaseDataService):
    """Service for fetching news data"""

    model_class = NewsArticle
    data_type = "news"
    cache_ttl = 3600 * 2  # 2 hours
    cache_max_ttl = 3600 * 6  # 6 hours
    etl_timeout = 10  # seconds

    @classmethod
    @adaptive_ttl_cache(base_ttl=3600 * 2, max_ttl=3600 * 6, error_ttl=300)
    def fetch_news(cls, symbol: str, days: int = 30) -> List[Dict[str, Any]]:
        """
        Public API to fetch news for a given stock symbol.
        Uses the base service pattern with specific handling for news data.
        """
        from models.db_models import SessionLocal

        session = SessionLocal()
        try:
            result = cls.fetch_data(session, symbol, days=days)
            return result.get("data", [])
        finally:
            session.close()

    @classmethod
    def _query_database(
        cls, session: Session, symbol: str, **kwargs
    ) -> List[NewsArticle]:
        """Query news articles from the database"""
        days = kwargs.get("days", 30)

        return (
            session.query(NewsArticle)
            .filter(NewsArticle.symbol == symbol)
            .order_by(desc(NewsArticle.datetime))
            .limit(days)  # Use days as limit for number of articles
            .all()
        )

    @classmethod
    def _format_records(
        cls, records: List[NewsArticle], source: str = "database"
    ) -> Dict[str, Any]:
        """Format news records for the API response"""
        data = []
        for record in records:
            article_data = {
                "headline": record.headline,
                "summary": record.summary,
                "url": record.url,
                "source": record.source,
                "datetime": int(record.datetime.timestamp())
                if record.datetime
                else None,
                "sentiment": record.sentiment,
                "category": record.category,
                "related": record.related,
                "image_url": record.image_url,
            }
            data.append(article_data)
        return {"data": data, "source": source}

    @classmethod
    def _run_etl_pipeline(cls, symbol: str) -> None:
        """Run the news ETL pipeline"""
        run_news_etl_pipeline(symbol)

    @classmethod
    def _try_alternative_sources(cls, symbol: str, **kwargs) -> Dict[str, Any]:
        """Try alternative data sources for news"""
        days = kwargs.get("days", 30)

        logger.info(f"No news found in database for {symbol}, trying direct API")

        # For news, we don't have alternative sources like Yahoo Finance
        # So we fall back directly to the legacy API call
        return cls._legacy_fetch_news(symbol, days)

    @classmethod
    @rate_limited_api(calls_per_minute=10)
    def _legacy_fetch_news(cls, symbol: str, days: int = 30) -> Dict[str, Any]:
        """Legacy method that directly calls the API."""
        end_date = datetime.today().strftime("%Y-%m-%d")
        start_date = (datetime.today() - timedelta(days=days)).strftime("%Y-%m-%d")

        url = "https://finnhub.io/api/v1/company-news"
        params = {
            "symbol": symbol,
            "from": start_date,
            "to": end_date,
            "token": Config.FINNHUB_API_KEY,
        }

        try:
            logger.info(f"[LEGACY] Fetching news for {symbol} via API")
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            articles = response.json()

            if isinstance(articles, list):
                # Add sentiment analysis to each article
                news_data = []
                for article in articles:
                    headline = article.get("headline", "")
                    sentiment_score = sia.polarity_scores(headline)["compound"]

                    news_item = {
                        "headline": headline,
                        "summary": article.get("summary", None),
                        "url": article.get("url", None),
                        "source": article.get("source", None),
                        "datetime": article.get("datetime", None),
                        "sentiment": sentiment_score,
                        "category": article.get("category", None),
                        "related": article.get("related", None),
                        "image_url": article.get("image", None),
                    }
                    news_data.append(news_item)

                logger.info(
                    f"[LEGACY] Retrieved {len(news_data)} news articles for {symbol}"
                )
                return {"data": news_data, "source": "finnhub"}
            else:
                logger.warning(f"[LEGACY] Unexpected news format for {symbol}")
                return {"data": [], "error": "No news data available"}

        except requests.exceptions.Timeout:
            logger.error(f"[LEGACY] Timeout fetching news for {symbol}")
            return {"data": [], "error": "API timeout"}
        except Exception as e:
            logger.error(f"[LEGACY] Error fetching news for {symbol}", exc_info=True)
            return {"data": [], "error": str(e)}
