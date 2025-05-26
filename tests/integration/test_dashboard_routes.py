"""
Integration tests for the dashboard routes and web UI.
Tests simulate actual user interactions with the web application.
"""

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest import mock

import flask
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import app
from models.db_models import Base, Earnings, FinancialReport, NewsArticle, StockPrice
from utils.cache import clear_cache


class TestDashboardRoutes(unittest.TestCase):
    """
    Integration tests for the dashboard routes and UI.
    Simulates user interactions with the web application.
    """

    @classmethod
    def setUpClass(cls):
        """Set up a test database and environment once for all tests"""
        # Create a temporary database for testing
        cls.temp_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls.temp_db_file.close()

        # Set up the database engine and create tables
        cls.engine = create_engine(f"sqlite:///{cls.temp_db_file.name}")
        Base.metadata.create_all(cls.engine)

        # Create a session factory
        cls.Session = sessionmaker(bind=cls.engine)

        # Configure the Flask app for testing
        app.config["TESTING"] = True
        app.config["DATABASE_URL"] = f"sqlite:///{cls.temp_db_file.name}"
        app.config["WTF_CSRF_ENABLED"] = False
        cls.client = app.test_client()

        # Store the app context
        cls.app = app

    @classmethod
    def tearDownClass(cls):
        """Clean up the test database"""
        os.unlink(cls.temp_db_file.name)

    def setUp(self):
        """Set up before each test"""
        # Create a fresh session
        self.session = self.Session()

        # Clear the database before each test
        for table in reversed(Base.metadata.sorted_tables):
            self.session.execute(table.delete())
        self.session.commit()

        # Clear any cached results
        clear_cache()

    def tearDown(self):
        """Clean up after each test"""
        self.session.close()

    def _populate_test_data(self, symbol="TEST"):
        """Helper to populate test data for a symbol"""
        # Add stock prices
        for i in range(30):
            price = StockPrice(
                symbol=symbol,
                date=datetime.now() - timedelta(days=i),
                open=100.0 - i * 0.5,
                high=101.0 - i * 0.5,
                low=99.0 - i * 0.5,
                close=100.5 - i * 0.5,
                volume=1000000 + i * 10000,
            )
            self.session.add(price)

        # Add financials
        for i in range(4):
            financial_report = FinancialReport(
                symbol=symbol,
                report_type="quarterly",
                year=2025 - (i // 4),
                quarter=4 - (i % 4),
                report_data={
                    "ic": [
                        {"concept": "Revenue", "value": 1000000 * (4 - i)},
                        {"concept": "Net Income", "value": 100000 * (4 - i)},
                    ]
                },
                filing_date=datetime.now() - timedelta(days=90 * i),
                fetched_at=datetime.now(),
            )
            self.session.add(financial_report)

        # Add earnings
        for i in range(4):
            earnings = Earnings(
                symbol=symbol,
                period=datetime.now() - timedelta(days=90 * i),
                quarter=4 - (i % 4),
                year=2025 - (i // 4),
                eps_actual=1.5 - (0.2 * i),
                eps_estimate=1.3 - (0.2 * i),
                eps_surprise=0.2,
                eps_surprise_percent=15.0,
                fetched_at=datetime.now(),
            )
            self.session.add(earnings)

        # Add news
        for i in range(5):
            news = NewsArticle(
                symbol=symbol,
                headline=f"Test News {i + 1} for {symbol}",
                summary=f"This is test news content {i + 1} for {symbol}.",
                url=f"https://example.com/news/{i + 1}",
                datetime=datetime.now() - timedelta(days=i * 3),
                sentiment=0.5 - (i * 0.2),
            )
            self.session.add(news)

        self.session.commit()

    def _set_session_mock(self):
        """Helper to mock the database session in the application"""
        patcher = mock.patch("models.db_models.SessionLocal", return_value=self.session)
        self.mock_session = patcher.start()
        self.addCleanup(patcher.stop)

    def test_index_route(self):
        """Test the main index route works and lists symbols"""
        self._populate_test_data("TEST")
        self._set_session_mock()

        response = self.client.get("/")

        # Check that the response is successful
        self.assertEqual(response.status_code, 200)

        # Check that the HTML contains the test symbol
        self.assertIn(b"TEST", response.data)

    def test_dashboard_route(self):
        """Test the dashboard route for a specific symbol"""
        self._populate_test_data("DASH")
        self._set_session_mock()

        response = self.client.get("/dashboard/DASH")

        # Check that the response is successful
        self.assertEqual(response.status_code, 200)

        # Check that the HTML contains expected elements
        self.assertIn(b"DASH", response.data)  # Symbol
        self.assertIn(b"Financial Data", response.data)  # Section title
        self.assertIn(b"chart-container", response.data)  # Chart container

    def test_api_endpoints(self):
        """Test the API endpoints that provide data to the dashboard"""
        self._populate_test_data("API")
        self._set_session_mock()

        # Test the stock data endpoint
        response = self.client.get("/api/stock_data/API")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn("prices", data)
        self.assertEqual(len(data["prices"]), 30)

        # Test the financial data endpoint
        response = self.client.get("/api/financials/API")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn("data", data)
        self.assertEqual(len(data["data"]), 4)

        # Test the news endpoint
        response = self.client.get("/api/news/API")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 5)

    def test_csv_export_feature(self):
        """Test the CSV export functionality"""
        self._populate_test_data("CSV")
        self._set_session_mock()

        # Test exporting stock data as CSV
        response = self.client.get("/api/export_stock_csv/CSV")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response.headers["Content-Type"])
        self.assertIn("attachment", response.headers["Content-Disposition"])

        # Check CSV content has headers and data
        csv_data = response.data.decode("utf-8")
        self.assertIn("Date,Open,High,Low,Close,Volume", csv_data)
        self.assertTrue(len(csv_data.splitlines()) > 1)

        # Test exporting financials as CSV
        response = self.client.get("/api/export_financials_csv/CSV")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response.headers["Content-Type"])
        csv_data = response.data.decode("utf-8")
        self.assertTrue(len(csv_data.splitlines()) > 1)

    @mock.patch("services.financials.fetch_financials")
    def test_error_handling(self, mock_fetch):
        """Test error handling in the dashboard routes"""
        # Setup mock to return an error
        mock_fetch.return_value = {"data": [], "error": "Test error message"}

        self._set_session_mock()

        # Test dashboard still loads with error
        response = self.client.get("/dashboard/ERROR")
        self.assertEqual(response.status_code, 200)

        # Test API endpoint with error
        response = self.client.get("/api/financials/ERROR")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn("error", data)
        self.assertEqual(data["error"], "Test error message")

    def test_performance(self):
        """Test performance aspects of the dashboard"""
        self._populate_test_data("PERF")
        self._set_session_mock()

        # Record time for initial request (should be uncached)
        import time

        start_time = time.time()
        self.client.get("/dashboard/PERF")
        first_request_time = time.time() - start_time

        # Record time for second request (should be cached)
        start_time = time.time()
        self.client.get("/dashboard/PERF")
        second_request_time = time.time() - start_time

        # Cached request should be significantly faster
        self.assertLess(second_request_time, first_request_time)

        # Test with query parameters that affect data ranges
        response = self.client.get("/dashboard/PERF?days=7")
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
