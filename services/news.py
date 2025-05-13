import requests
from datetime import datetime, timedelta
from config import Config
from utils.logging_config import logger


def fetch_company_news(symbol, days=30):
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    url = "https://finnhub.io/api/v1/company-news"
    params = {
        "symbol": symbol,
        "from": start_date.isoformat(),
        "to": end_date.isoformat(),
        "token": Config.FINNHUB_API_KEY,
    }
    try:
        logger.info(
            f"Fetching news for {symbol} from {start_date} to {end_date} - URL: {url} with params: {params}"
        )
        response = requests.get(url, params=params)
        response.raise_for_status()
        news = response.json()
        for article in news:
            article["sentiment"] = 0  # Placeholder
        logger.info(f"Fetched {len(news)} articles for {symbol}")
        return news
    except Exception as e:
        logger.error(f"Error fetching news for {symbol}: {e}", exc_info=True)
        return []
