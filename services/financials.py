import requests
from config import Config
from utils.logging_config import logger
from utils.cache import timed_cache


@timed_cache(expire_seconds=3600 * 12)  # Cache for 12 hours - financials rarely change
def fetch_financials(symbol: str, freq: str = "quarterly"):
    """
    Fetches financials (reported) for a given stock symbol from Finnhub.
    By default, it pulls quarterly data. You can set freq='annual' to override.
    """
    url = "https://finnhub.io/api/v1/stock/financials-reported"
    params = {
        "symbol": symbol,
        "token": Config.FINNHUB_API_KEY,
        "freq": freq,
    }

    try:
        logger.info(f"Fetching financials for {symbol} - Params: {params}")
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
            logger.info(
                f"Financials received for {symbol}: {len(data['data'])} records"
            )
            return data  # expected structure
        elif isinstance(data, list):  # fallback case
            logger.warning(
                f"Unexpected format: financials returned as list for {symbol}"
            )
            return {"data": data}
        else:
            logger.warning(f"Unexpected financials format for {symbol}: {type(data)}")
            return {"data": []}

    except Exception as e:
        logger.error(f"Error fetching financials for {symbol}", exc_info=True)
        return {"data": []}
