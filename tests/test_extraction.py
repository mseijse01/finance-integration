from unittest.mock import Mock, patch

import pytest
import requests

from etl.extraction import fetch_stock_data


@pytest.fixture
def mock_response():
    mock_resp = Mock()
    mock_resp.json.return_value = {
        "Time Series (Daily)": {
            "2024-05-01": {
                "1. open": "10.0",
                "2. high": "10.5",
                "3. low": "9.8",
                "4. close": "10.2",
                "5. volume": "1000000",
            }
        }
    }
    return mock_resp


def test_fetch_stock_data_success(mock_response):
    with patch("requests.get") as mock_get:
        mock_get.return_value = mock_response
        mock_response.status_code = 200

        result = fetch_stock_data("TEST")

        assert "Time Series (Daily)" in result
        assert "2024-05-01" in result["Time Series (Daily)"]
        mock_get.assert_called_once()


def test_fetch_stock_data_with_custom_function(mock_response):
    with patch("requests.get") as mock_get:
        mock_get.return_value = mock_response
        mock_response.status_code = 200

        result = fetch_stock_data("TEST", function="TIME_SERIES_WEEKLY")

        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert kwargs["params"]["function"] == "TIME_SERIES_WEEKLY"


def test_fetch_stock_data_api_error():
    with patch("requests.get") as mock_get:
        mock_response = Mock()
        mock_response.json.return_value = {"Error Message": "Invalid API call"}
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        with pytest.raises(ValueError, match="API error"):
            fetch_stock_data("INVALID")


def test_fetch_stock_data_request_exception():
    with patch("requests.get") as mock_get:
        mock_get.side_effect = requests.exceptions.RequestException("Connection error")

        with pytest.raises(requests.exceptions.RequestException):
            fetch_stock_data("TEST")
