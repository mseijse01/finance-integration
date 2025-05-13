import requests
from config import Config
from utils.logging_config import logger


def fetch_financials(symbol):
    url = f"https://finnhub.io/api/v1/stock/financials-reported?symbol={symbol}&token={Config.FINNHUB_API_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data
    except Exception as e:
        logger.error(f"Error fetching financials for {symbol}: {e}", exc_info=True)
        return {}
