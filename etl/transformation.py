from datetime import datetime

import polars as pl

from utils.logging_config import logger


def transform_stock_data(raw_data: dict, symbol: str) -> pl.DataFrame:
    """
    Transforms raw JSON data from Alpha Vantage into a Polars DataFrame.
    Computes metrics like 20-day moving average and volatility.
    """
    try:
        logger.info("[Transformation] Starting data transformation")
        time_series = raw_data.get("Time Series (Daily)", {})
        if not time_series:
            raise ValueError("No time series data found in the API response.")

        records = []
        for date_str, metrics in time_series.items():
            try:
                record_date = datetime.strptime(date_str, "%Y-%m-%d")
            except Exception:
                logger.warning(
                    f"Skipping record with invalid date format: {date_str}",
                    exc_info=True,
                )
                continue

            records.append(
                {
                    "date": record_date,
                    "symbol": symbol,
                    "open": float(metrics.get("1. open", 0)),
                    "high": float(metrics.get("2. high", 0)),
                    "low": float(metrics.get("3. low", 0)),
                    "close": float(metrics.get("4. close", 0)),
                    "volume": int(metrics.get("5. volume", 0)),
                }
            )

        if not records:
            raise ValueError("No valid records found to transform.")

        df = pl.DataFrame(records).sort("date")

        # Compute rolling metrics
        df = df.with_columns(
            [
                pl.col("close").rolling_mean(window_size=20).alias("moving_average_20"),
            ]
        )

        logger.info("[Transformation] Data transformation completed")
        return df
    except Exception:
        logger.error("Error during data transformation", exc_info=True)
        raise
