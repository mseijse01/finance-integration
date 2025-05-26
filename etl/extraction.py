import requests

from config import Config
from utils.logging_config import logger


def fetch_stock_data(symbol: str, function: str = "TIME_SERIES_DAILY"):
    """
    Fetches daily time series data for a given stock symbol from Alpha Vantage.
    """
    base_url = "https://www.alphavantage.co/query"
    params = {
        "function": function,
        "symbol": symbol,
        "apikey": Config.ALPHA_VANTAGE_API_KEY,
        "outputsize": "full",  # or "full" for complete history
    }

    try:
        logger.info(f"[Extraction] Fetching data for symbol: {symbol}")
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()
        if "Error Message" in data:
            raise ValueError(f"API error: {data['Error Message']}")
        logger.info("[Extraction] Data fetched successfully")
        return data
    except requests.exceptions.RequestException:
        logger.error("Request error while fetching data", exc_info=True)
        raise
    except Exception:
        logger.error("Unexpected error during extraction", exc_info=True)
        raise
