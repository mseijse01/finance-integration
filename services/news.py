import requests
from config import Config
from utils.logging_config import logger
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import nltk
from utils.cache import timed_cache
from models.db_models import SessionLocal, NewsArticle
from sqlalchemy import desc
from datetime import datetime, timedelta
from etl.news_etl import run_news_etl_pipeline
import ssl
from flask import Blueprint, render_template
from utils.constants import CacheTTL
import concurrent.futures
import threading

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

news_bp = Blueprint("news", __name__)

# Global thread pool for parallel ETL operations
ETL_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=2)
ETL_TIMEOUT = 10  # seconds

# Thread-local storage for ETL operations in progress
_etl_operations = threading.local()


@timed_cache(expire_seconds=CacheTTL.NEWS_CACHE)  # Use constant instead of magic number
def fetch_company_news(symbol, days=30):
    """
    Fetch recent news articles for a given stock symbol from the database.
    Falls back to ETL pipeline if no recent data is found.
    """
    session = SessionLocal()
    try:
        # Calculate date threshold for "recent" news
        recent_date = datetime.now() - timedelta(
            days=1
        )  # Consider news older than 1 day as potentially stale

        # Check if we have any recent news
        recent_news = (
            session.query(NewsArticle)
            .filter(NewsArticle.symbol == symbol, NewsArticle.fetched_at >= recent_date)
            .first()
        )

        # If no recent news, trigger the ETL pipeline to fetch fresh data
        if not recent_news:
            logger.info(f"No recent news found for {symbol}, triggering ETL pipeline")
            run_news_etl_pipeline(symbol)

        # Query the database for news articles
        news_records = (
            session.query(NewsArticle)
            .filter(NewsArticle.symbol == symbol)
            .order_by(desc(NewsArticle.datetime))
            .limit(days)
            .all()
        )

        # Convert to the format expected by the dashboard
        articles = []
        for record in news_records:
            article = {
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
            }
            articles.append(article)

        logger.info(f"Fetched {len(articles)} articles for {symbol} from database")
        return articles
    except Exception as e:
        logger.error(
            f"Error fetching news for {symbol} from database: {e}", exc_info=True
        )
        # Fallback to the original API call if database access fails
        return _legacy_fetch_company_news(symbol, days)
    finally:
        session.close()


def _legacy_fetch_company_news(symbol, days=30):
    """
    Legacy method that directly calls the API.
    Used as fallback if database access fails.
    """
    from datetime import datetime, timedelta

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
        response = requests.get(url, params=params)
        response.raise_for_status()
        articles = response.json()

        for article in articles:
            headline = article.get("headline", "")
            sentiment_score = sia.polarity_scores(headline)["compound"]
            article["sentiment"] = sentiment_score

        logger.info(f"[LEGACY] Fetched {len(articles)} articles for {symbol}")
        return articles
    except Exception as e:
        logger.error(f"[LEGACY] Error fetching news for {symbol}: {e}", exc_info=True)
        return []
