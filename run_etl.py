# run_etl.py

from etl.extraction import fetch_stock_data
from etl.transformation import transform_stock_data
from etl.loading import load_data_to_db
from utils.logging_config import logger


def run_pipeline(symbol: str):
    try:
        logger.info(f"[ETL] Starting pipeline for {symbol}")
        raw_data = fetch_stock_data(symbol)
        transformed_df = transform_stock_data(raw_data, symbol)
        load_data_to_db(transformed_df)
        logger.info(f"[ETL] Pipeline completed for {symbol}")
    except Exception as e:
        logger.error(f"[ETL] Pipeline failed for {symbol}", exc_info=True)


if __name__ == "__main__":
    symbols = ["CGC", "ACB", "CRON", "TLRY"]
    for symbol in symbols:
        run_pipeline(symbol)
