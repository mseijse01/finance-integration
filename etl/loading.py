import datetime

from models.db_models import SessionLocal, StockPrice
from utils.logging_config import logger


def load_data_to_db(df):
    """
    Inserts records from the Polars DataFrame into the stock_prices table.
    """
    session = SessionLocal()
    try:
        logger.info("[Loading] Loading data into the database")
        records = df.to_dicts()
        for record in records:
            if isinstance(record["date"], datetime.datetime):
                record["date"] = record["date"].date()

            stock_price = StockPrice(**record)
            session.add(stock_price)
        session.commit()
        logger.info("[Loading] Data loaded successfully")
    except Exception:
        session.rollback()
        logger.error("Error loading data into the database", exc_info=True)
        raise
    finally:
        session.close()
