from unittest.mock import Mock, patch

import pytest
import requests

from services.earnings import fetch_earnings


@pytest.fixture
def mock_earnings_response():
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [
        {"actual": 0.15, "estimate": 0.12, "period": "2024-03-31", "symbol": "TEST"},
        {"actual": 0.11, "estimate": 0.10, "period": "2023-12-31", "symbol": "TEST"},
    ]
    return mock_resp


def test_fetch_earnings_success(mock_earnings_response):
    with patch("requests.get") as mock_get:
        mock_get.return_value = mock_earnings_response

        result = fetch_earnings("TEST")

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["symbol"] == "TEST"
        assert result[1]["period"] == "2023-12-31"
        mock_get.assert_called_once()


def test_fetch_earnings_params():
    with patch("requests.get") as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        fetch_earnings("TEST")

        args, kwargs = mock_get.call_args
        assert kwargs["params"]["symbol"] == "TEST"
        assert kwargs["params"]["freq"] == "quarterly"


def test_fetch_earnings_unexpected_format():
    with patch("requests.get") as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"error": "Invalid symbol"}
        mock_get.return_value = mock_response

        result = fetch_earnings("INVALID")

        assert not isinstance(result, list)  # Should not be a list
        assert isinstance(result, dict)


def test_fetch_earnings_request_exception():
    with patch("requests.get") as mock_get:
        mock_get.side_effect = requests.exceptions.RequestException("Connection error")

        result = fetch_earnings("TEST")

        assert isinstance(result, list)
        assert len(result) == 0  # Empty list returned on error
