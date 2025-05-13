import requests
from config import Config
from utils.logging_config import logger


def fetch_earnings(symbol):
    url = f"https://finnhub.io/api/v1/stock/earnings?symbol={symbol}&token={Config.FINNHUB_API_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching earnings for {symbol}: {e}", exc_info=True)
        return []
