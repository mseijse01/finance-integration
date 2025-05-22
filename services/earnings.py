import requests
from config import Config
from utils.logging_config import logger
from utils.cache import timed_cache


@timed_cache(
    expire_seconds=3600 * 24
)  # Cache for 24 hours - earnings reports are quarterly
def fetch_earnings(symbol: str):
    url = "https://finnhub.io/api/v1/stock/earnings"
    params = {
        "symbol": symbol,
        "token": Config.FINNHUB_API_KEY,
        "freq": "quarterly",  # <-- Ensure quarterly data
    }

    try:
        logger.info(f"Fetching earnings for {symbol} - Params: {params}")
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list):
            logger.info(f"Earnings received for {symbol}: {len(data)} records")
        else:
            logger.warning(f"Unexpected earnings format for {symbol}: {data}")
        return data
    except Exception as e:
        logger.error(f"Error fetching earnings for {symbol}", exc_info=True)
        return []
