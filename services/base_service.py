"""
Base service class providing common functionality for data services
"""

import concurrent.futures
import threading
from datetime import datetime
from typing import Any, Callable, Dict, Generic, List, Optional, Type, TypeVar

from sqlalchemy.orm import Session

from utils.cache import adaptive_ttl_cache
from utils.logging_config import logger

# Global thread pool for parallel ETL operations
ETL_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=4)

# Thread-local storage for ETL operations in progress
_etl_operations = threading.local()


class BaseDataService:
    """Generic base class for data services"""

    # These should be overridden by subclasses
    model_class = None
    data_type = "generic"
    cache_ttl = 3600 * 6  # 6 hours
    cache_max_ttl = 3600 * 24  # 24 hours
    etl_timeout = 15  # seconds

    @classmethod
    def fetch_data(cls, session: Session, symbol: str, **kwargs) -> Dict[str, Any]:
        """
        Generic data fetching method that follows the pattern:
        1. Try database
        2. If not found, trigger ETL
        3. Check database again
        4. Try alternative sources
        5. Fall back to hardcoded data
        """
        # Fast path - check if we have data in the database first
        records = cls._query_database(session, symbol, **kwargs)

        # If we have data, return it immediately
        if records:
            logger.info(
                f"Fetched {len(records)} {cls.data_type} records for {symbol} from database"
            )
            return cls._format_records(records, source="database")

        # No data in database - need to find a source
        logger.info(
            f"No {cls.data_type} found in database for {symbol}, trying alternatives"
        )

        # Check if ETL is already running for this symbol
        etl_key = f"{symbol}_{cls.data_type}_etl_running"
        is_etl_running = getattr(_etl_operations, etl_key, False)

        if not is_etl_running:
            # Mark ETL as running
            setattr(_etl_operations, etl_key, True)
            try:
                # Try running ETL pipeline with a timeout
                logger.info(
                    f"Triggering {cls.data_type} ETL pipeline for {symbol} with {cls.etl_timeout}s timeout"
                )
                future = ETL_EXECUTOR.submit(cls._run_etl_pipeline, symbol)
                future.result(
                    timeout=cls.etl_timeout
                )  # Wait for ETL to complete with timeout

                # Check if ETL produced data
                records = cls._query_database(session, symbol, **kwargs)
                if records:
                    logger.info(
                        f"ETL pipeline successfully fetched {cls.data_type} for {symbol}"
                    )
                    return cls._format_records(records, source="database")
            except concurrent.futures.TimeoutError:
                logger.warning(
                    f"ETL pipeline timed out after {cls.etl_timeout}s for {symbol}"
                )
            except Exception as e:
                logger.error(f"Error in ETL pipeline for {symbol}: {e}")
            finally:
                # Reset ETL running flag
                setattr(_etl_operations, etl_key, False)
        else:
            logger.info(f"{cls.data_type} ETL already running for {symbol}, skipping")

        # Try alternative data sources
        return cls._try_alternative_sources(symbol, **kwargs)

    @classmethod
    def _query_database(cls, session: Session, symbol: str, **kwargs) -> List[Any]:
        """Query the database for records. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement _query_database")

    @classmethod
    def _format_records(
        cls, records: List[Any], source: str = "database"
    ) -> Dict[str, Any]:
        """Format records for the API response. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement _format_records")

    @classmethod
    def _run_etl_pipeline(cls, symbol: str) -> None:
        """Run the ETL pipeline. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement _run_etl_pipeline")

    @classmethod
    def _try_alternative_sources(cls, symbol: str, **kwargs) -> Dict[str, Any]:
        """Try alternative data sources. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement _try_alternative_sources")
