import json
from unittest.mock import MagicMock, Mock, patch

import pandas as pd
import pytest

from app import app
from models.db_models import StockPrice
from views.dashboard import download_csv


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_db_records():
    records = [
        {
            "id": 1,
            "symbol": "TEST",
            "date": "2024-05-01",
            "open": 10.0,
            "high": 10.5,
            "low": 9.8,
            "close": 10.2,
            "volume": 1000000,
            "moving_average_20": 10.1,
            "volatility": 0.05,
        },
        {
            "id": 2,
            "symbol": "TEST",
            "date": "2024-04-30",
            "open": 9.5,
            "high": 10.0,
            "low": 9.4,
            "close": 9.8,
            "volume": 900000,
            "moving_average_20": 9.9,
            "volatility": 0.06,
        },
    ]
    return records


@pytest.fixture
def mock_raw_data():
    return {
        "Time Series (Daily)": {
            "2024-05-01": {
                "1. open": "10.0",
                "2. high": "10.5",
                "3. low": "9.8",
                "4. close": "10.2",
                "5. volume": "1000000",
            },
            "2024-04-30": {
                "1. open": "9.5",
                "2. high": "10.0",
                "3. low": "9.4",
                "4. close": "9.8",
                "5. volume": "900000",
            },
        }
    }


def test_download_csv_transformed_data(client, mock_db_records):
    with patch("views.dashboard.SessionLocal") as mock_session_local:
        # Setup mock session
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session

        # Setup mock query
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query

        # Mock query results
        mock_stock_prices = []
        for record in mock_db_records:
            stock_price = MagicMock(spec=StockPrice)
            stock_price.__dict__ = {**record, "_sa_instance_state": None}
            mock_stock_prices.append(stock_price)

        mock_query.__iter__.return_value = mock_stock_prices

        # Make request
        response = client.get("/download/TEST")

        # Check response
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "text/csv"
        assert (
            "attachment;filename=TEST_transformed_data_"
            in response.headers["Content-Disposition"]
        )

        # Check CSV content
        content = response.data.decode("utf-8")
        assert (
            "symbol,date,open,high,low,close,volume,moving_average_20,volatility"
            in content
        )
        assert (
            "TEST,2024-05-01,10.0,10.5,9.8,10.2,1000000.0,10.1,0.05"
            in content.replace(" ", "")
        )


def test_download_csv_raw_data(client, mock_raw_data):
    with patch("views.dashboard.fetch_stock_data") as mock_fetch:
        mock_fetch.return_value = mock_raw_data

        # Make request
        response = client.get("/download/TEST?data_type=raw")

        # Check response
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "text/csv"
        assert (
            "attachment;filename=TEST_raw_data_"
            in response.headers["Content-Disposition"]
        )

        # Check CSV content
        content = response.data.decode("utf-8")
        assert "date,open,high,low,close,volume" in content
        assert "2024-05-01,10.0,10.5,9.8,10.2,1000000" in content.replace(" ", "")


def test_download_csv_no_data():
    with (
        patch("app.app_context"),
        patch("views.dashboard.SessionLocal") as mock_session_local,
    ):
        # Setup mock session with no data
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session

        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.__iter__.return_value = []

        # Create Flask test client and make request
        with app.test_client() as client:
            response = client.get("/download/INVALID")

            # Check response
            assert response.status_code == 404
            assert b"No data available for this symbol" in response.data


def test_download_csv_api_error():
    with (
        patch("app.app_context"),
        patch("views.dashboard.fetch_stock_data") as mock_fetch,
    ):
        mock_fetch.side_effect = Exception("API Error")

        # Create Flask test client and make request
        with app.test_client() as client:
            response = client.get("/download/TEST?data_type=raw")

            # Check response
            assert response.status_code == 500
            assert b"Error fetching data" in response.data
