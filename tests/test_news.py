from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest
import requests

from services.news import fetch_company_news


@pytest.fixture
def mock_news_response():
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [
        {
            "id": 1,
            "headline": "Company XYZ Announces New Product",
            "datetime": 1717027521,  # Unix timestamp
            "source": "Financial Times",
            "summary": "Company XYZ announced a new product today.",
        },
        {
            "id": 2,
            "headline": "Company XYZ Stock Up 5%",
            "datetime": 1716941121,  # Unix timestamp
            "source": "Bloomberg",
            "summary": "Company XYZ's stock increased by 5% today.",
        },
    ]
    return mock_resp


def test_fetch_company_news_success(mock_news_response):
    with (
        patch("requests.get") as mock_get,
        patch(
            "nltk.sentiment.vader.SentimentIntensityAnalyzer.polarity_scores"
        ) as mock_sentiment,
    ):
        mock_get.return_value = mock_news_response
        mock_sentiment.return_value = {
            "compound": 0.5,
            "pos": 0.7,
            "neg": 0.0,
            "neu": 0.3,
        }

        result = fetch_company_news("TEST")

        assert isinstance(result, list)
        assert len(result) == 2
        assert "sentiment" in result[0]
        assert result[0]["sentiment"] == 0.5
        mock_get.assert_called_once()


def test_fetch_company_news_custom_days():
    with patch("requests.get") as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        fetch_company_news("TEST", days=60)

        args, kwargs = mock_get.call_args

        today = datetime.today()
        sixty_days_ago = (today - timedelta(days=60)).strftime("%Y-%m-%d")
        today_str = today.strftime("%Y-%m-%d")

        assert kwargs["params"]["from"] == sixty_days_ago
        assert kwargs["params"]["to"] == today_str


def test_fetch_company_news_empty_response():
    with (
        patch("requests.get") as mock_get,
        patch(
            "nltk.sentiment.vader.SentimentIntensityAnalyzer.polarity_scores"
        ) as mock_sentiment,
    ):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response
        mock_sentiment.return_value = {"compound": 0.0}

        result = fetch_company_news("TEST")

        assert isinstance(result, list)
        assert len(result) == 0
        # Sentiment analyzer should not be called for empty results
        mock_sentiment.assert_not_called()


def test_fetch_company_news_request_exception():
    with patch("requests.get") as mock_get:
        mock_get.side_effect = requests.exceptions.RequestException("Connection error")

        result = fetch_company_news("TEST")

        assert isinstance(result, list)
        assert len(result) == 0  # Empty list returned on error
