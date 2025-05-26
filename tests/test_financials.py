from unittest.mock import Mock, patch

import pytest
import requests

from services.financials import fetch_financials


@pytest.fixture
def mock_success_response():
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": [
            {
                "year": 2024,
                "quarter": 1,
                "form": "10-Q",
                "report": {"ic": [{"concept": "Revenue", "value": 1000000}]},
            }
        ]
    }
    return mock_resp


def test_fetch_financials_success(mock_success_response):
    with patch("requests.get") as mock_get:
        mock_get.return_value = mock_success_response

        result = fetch_financials("TEST")

        assert "data" in result
        assert isinstance(result["data"], list)
        assert len(result["data"]) == 1
        mock_get.assert_called_once()


def test_fetch_financials_with_annual_freq():
    with patch("requests.get") as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}
        mock_get.return_value = mock_response

        fetch_financials("TEST", freq="annual")

        args, kwargs = mock_get.call_args
        assert kwargs["params"]["freq"] == "annual"


def test_fetch_financials_list_fallback():
    with patch("requests.get") as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"year": 2024, "quarter": 1}]
        mock_get.return_value = mock_response

        result = fetch_financials("TEST")

        assert "data" in result
        assert isinstance(result["data"], list)


def test_fetch_financials_unexpected_format():
    with patch("requests.get") as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = "Invalid data"
        mock_get.return_value = mock_response

        result = fetch_financials("TEST")

        assert "data" in result
        assert isinstance(result["data"], list)
        assert len(result["data"]) == 0


def test_fetch_financials_request_exception():
    with patch("requests.get") as mock_get:
        mock_get.side_effect = requests.exceptions.RequestException("Connection error")

        result = fetch_financials("TEST")

        assert "data" in result
        assert len(result["data"]) == 0
