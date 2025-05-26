# run_etl.py

import concurrent.futures
import time

from etl.earnings_etl import run_earnings_etl_pipeline
from etl.extraction import fetch_stock_data
from etl.financials_etl import run_financials_etl_pipeline
from etl.loading import load_data_to_db
from etl.news_etl import run_news_etl_pipeline
from etl.transformation import transform_stock_data
from models.db_models import create_tables
from utils.logging_config import logger


def run_stock_price_pipeline(symbol: str):
    try:
        logger.info(f"[Stock ETL] Starting pipeline for {symbol}")
        raw_data = fetch_stock_data(symbol)
        transformed_df = transform_stock_data(raw_data, symbol)
        load_data_to_db(transformed_df)
        logger.info(f"[Stock ETL] Pipeline completed for {symbol}")
        return True
    except Exception as e:
        logger.error(f"[Stock ETL] Pipeline failed for {symbol}: {e}", exc_info=True)
        return False


def run_pipeline_for_symbol(symbol: str):
    """Run all ETL pipelines for a given symbol"""
    success = {
        "stock_prices": run_stock_price_pipeline(symbol),
        "news": run_news_etl_pipeline(symbol),
        "financials": run_financials_etl_pipeline(symbol),
        "earnings": run_earnings_etl_pipeline(symbol),
    }

    logger.info(f"ETL pipeline results for {symbol}: {success}")
    return all(success.values())


def run_pipelines_parallel(symbols, max_workers=4):
    """Run ETL pipelines for multiple symbols in parallel"""
    start_time = time.time()
    logger.info(f"[ETL] Starting parallel ETL pipeline for {len(symbols)} symbols")

    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_symbol = {
            executor.submit(run_pipeline_for_symbol, symbol): symbol
            for symbol in symbols
        }
        for future in concurrent.futures.as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            try:
                success = future.result()
                results[symbol] = success
            except Exception as e:
                logger.error(
                    f"[ETL] Parallel pipeline execution failed for {symbol}: {e}",
                    exc_info=True,
                )
                results[symbol] = False

    elapsed_time = time.time() - start_time
    logger.info(f"[ETL] All pipelines completed in {elapsed_time:.2f} seconds")
    logger.info(f"[ETL] Results: {results}")

    return results


if __name__ == "__main__":
    # Ensure all tables exist
    create_tables()

    # Define default symbols to process
    symbols = ["SBUX", "KDP", "BROS", "FARM"]

    # Run pipelines in parallel
    run_pipelines_parallel(symbols)
