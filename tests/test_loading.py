import datetime
from unittest.mock import MagicMock, patch

import polars as pl
import pytest

from etl.loading import load_data_to_db
from models.db_models import StockPrice


@pytest.fixture
def sample_dataframe():
    return pl.DataFrame(
        {
            "symbol": ["TEST", "TEST"],
            "date": [datetime.datetime(2024, 5, 1), datetime.datetime(2024, 4, 30)],
            "open": [10.0, 9.5],
            "high": [10.5, 10.0],
            "low": [9.8, 9.4],
            "close": [10.2, 9.8],
            "volume": [1000000, 900000],
            "moving_average_20": [10.1, 9.9],
            "volatility": [0.05, 0.06],
        }
    )


def test_load_data_to_db_success(sample_dataframe):
    mock_session = MagicMock()

    with patch("etl.loading.SessionLocal", return_value=mock_session):
        load_data_to_db(sample_dataframe)

        # Check if session.add was called twice (once for each row)
        assert mock_session.add.call_count == 2

        # Check if commit was called
        mock_session.commit.assert_called_once()

        # Check if close was called
        mock_session.close.assert_called_once()


def test_load_data_to_db_with_datetime_conversion(sample_dataframe):
    mock_session = MagicMock()

    with patch("etl.loading.SessionLocal", return_value=mock_session):
        load_data_to_db(sample_dataframe)

        # Get the first call arguments
        args, _ = mock_session.add.call_args_list[0]
        stock_price_obj = args[0]

        # Check if date was converted from datetime to date
        assert isinstance(stock_price_obj.date, datetime.date)
        assert not isinstance(stock_price_obj.date, datetime.datetime)


def test_load_data_to_db_exception_handling():
    mock_session = MagicMock()
    mock_session.commit.side_effect = Exception("Database error")

    with patch("etl.loading.SessionLocal", return_value=mock_session):
        with pytest.raises(Exception):
            load_data_to_db(pl.DataFrame({"symbol": ["TEST"]}))

        # Check if rollback was called
        mock_session.rollback.assert_called_once()

        # Check if close was called even after exception
        mock_session.close.assert_called_once()


def test_load_data_to_db_empty_dataframe():
    mock_session = MagicMock()
    empty_df = pl.DataFrame(
        {
            "symbol": [],
            "date": [],
            "open": [],
            "high": [],
            "low": [],
            "close": [],
            "volume": [],
            "moving_average_20": [],
            "volatility": [],
        }
    )

    with patch("etl.loading.SessionLocal", return_value=mock_session):
        load_data_to_db(empty_df)

        # No records should be added
        assert mock_session.add.call_count == 0

        # Commit should still be called
        mock_session.commit.assert_called_once()
