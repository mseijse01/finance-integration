import requests
from config import Config
from utils.logging_config import logger
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import nltk

# Ensure the lexicon is available
nltk.download("vader_lexicon", quiet=True)
sia = SentimentIntensityAnalyzer()


def fetch_company_news(symbol, days=30):
    """
    Fetch recent news articles for a given stock symbol and attach sentiment scores using VADER.
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
        logger.info(
            f"Fetching news for {symbol} from {start_date} to {end_date} - URL: {url} - Params: {params}"
        )
        response = requests.get(url, params=params)
        response.raise_for_status()
        articles = response.json()

        for article in articles:
            headline = article.get("headline", "")
            sentiment_score = sia.polarity_scores(headline)["compound"]
            article["sentiment"] = sentiment_score

        logger.info(f"Fetched {len(articles)} articles for {symbol}")
        return articles
    except Exception as e:
        logger.error(f"Error fetching news for {symbol}: {e}", exc_info=True)
        return []
