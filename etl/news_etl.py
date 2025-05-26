import ssl
from datetime import datetime, timedelta

import nltk
import requests
from nltk.sentiment.vader import SentimentIntensityAnalyzer

from config import Config
from models.db_models import NewsArticle, SessionLocal
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


def extract_company_news(symbol, days=30):
    """
    Extract recent news articles for a given stock symbol.
    """
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
        logger.info(
            f"[News ETL] Extracting news for {symbol} from {start_date} to {end_date}"
        )
        response = requests.get(url, params=params)
        response.raise_for_status()
        articles = response.json()
        logger.info(f"[News ETL] Extracted {len(articles)} articles for {symbol}")
        return articles
    except Exception as e:
        logger.error(
            f"[News ETL] Error extracting news for {symbol}: {e}", exc_info=True
        )
        return []


def transform_news_data(articles, symbol):
    """
    Transform news data by adding sentiment analysis and normalizing structure.
    """
    try:
        logger.info(
            f"[News ETL] Transforming {len(articles)} news articles for {symbol}"
        )
        transformed_articles = []

        for article in articles:
            # Apply sentiment analysis
            headline = article.get("headline", "")
            sentiment_score = sia.polarity_scores(headline)["compound"]

            # Create a normalized article structure
            transformed_article = {
                "symbol": symbol,
                "headline": headline,
                "summary": article.get("summary", None),
                "url": article.get("url", None),
                "source": article.get("source", None),
                "datetime": datetime.fromtimestamp(article.get("datetime", 0)),
                "sentiment": sentiment_score,
                "category": article.get("category", None),
                "related": article.get("related", None),
                "image_url": article.get("image", None),
            }

            transformed_articles.append(transformed_article)

        logger.info(
            f"[News ETL] Transformed {len(transformed_articles)} articles for {symbol}"
        )
        return transformed_articles
    except Exception as e:
        logger.error(
            f"[News ETL] Error transforming news for {symbol}: {e}", exc_info=True
        )
        return []


def load_news_to_db(transformed_articles):
    """
    Load transformed news articles into the database.
    """
    session = SessionLocal()
    try:
        logger.info(
            f"[News ETL] Loading {len(transformed_articles)} articles to database"
        )

        # For each article, create or update the database record
        for article_data in transformed_articles:
            # Check if the article already exists by URL and datetime
            existing = (
                session.query(NewsArticle)
                .filter_by(
                    symbol=article_data["symbol"],
                    headline=article_data["headline"],
                    datetime=article_data["datetime"],
                )
                .first()
            )

            if existing:
                # Update existing record
                for key, value in article_data.items():
                    setattr(existing, key, value)
            else:
                # Create new record
                article = NewsArticle(**article_data)
                session.add(article)

        session.commit()
        logger.info("[News ETL] News data loaded successfully")
    except Exception as e:
        session.rollback()
        logger.error(f"[News ETL] Error loading news data: {e}", exc_info=True)
    finally:
        session.close()


def run_news_etl_pipeline(symbol):
    """
    Run the full ETL pipeline for news data.
    """
    try:
        logger.info(f"[News ETL] Starting news ETL pipeline for {symbol}")
        raw_news = extract_company_news(symbol)
        if raw_news:
            transformed_news = transform_news_data(raw_news, symbol)
            if transformed_news:
                load_news_to_db(transformed_news)
        logger.info(f"[News ETL] News ETL pipeline completed for {symbol}")
        return True
    except Exception as e:
        logger.error(
            f"[News ETL] News ETL pipeline failed for {symbol}: {e}", exc_info=True
        )
        return False
