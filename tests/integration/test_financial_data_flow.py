"""
Integration tests for the complete financial data flow.
Tests the entire pipeline from API to ETL to database to dashboard.
"""

import json
import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest import mock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.db_models import Base, Earnings, FinancialReport, NewsArticle, StockPrice
from services.alternative_financials import fetch_yahoo_financials

# Import services directly (service layer cleanup completed)
from services.earnings import EarningsService
from services.financials import FinancialsService
from utils.cache import clear_cache


class TestFinancialDataFlow(unittest.TestCase):
    """
    Integration tests for the complete financial data flow.
    Tests entire features rather than individual units.
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

        # Mock the environment variables
        os.environ["DATABASE_URL"] = f"sqlite:///{cls.temp_db_file.name}"

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

    def test_financial_data_flow_with_database_data(self):
        """Test the financial data flow when data exists in the database"""
        # Populate test data in the database
        symbol = "TEST"

        # Add financial reports
        for i in range(4):
            financial_report = FinancialReport(
                symbol=symbol,
                report_type="quarterly",
                year=2025,
                quarter=4 - i,
                report_data={
                    "ic": [
                        {"concept": "Revenue", "value": 1000000 * (i + 1)},
                        {"concept": "Net Income", "value": 100000 * (i + 1)},
                    ]
                },
                filing_date=datetime.now() - timedelta(days=90 * i),
                fetched_at=datetime.now(),
            )
            self.session.add(financial_report)

        # Add earnings data
        for i in range(4):
            earnings = Earnings(
                symbol=symbol,
                period=datetime.now() - timedelta(days=90 * i),
                quarter=4 - i,
                year=2025,
                eps_actual=1.5 - (0.2 * i),
                eps_estimate=1.3 - (0.2 * i),
                eps_surprise=0.2,
                eps_surprise_percent=15.0,
                fetched_at=datetime.now(),
            )
            self.session.add(earnings)

        self.session.commit()

        # Test the original financials service
        with mock.patch("models.db_models.SessionLocal", return_value=self.session):
            # Test fetching financials
            financials_data = FinancialsService.fetch_financials(symbol)
            self.assertIsNotNone(financials_data)
            self.assertEqual(len(financials_data["data"]), 4)
            self.assertEqual(financials_data["source"], "finnhub")

            # Test fetching earnings
            earnings_data = EarningsService.fetch_earnings(symbol)
            self.assertIsNotNone(earnings_data)
            self.assertEqual(len(earnings_data), 4)
            self.assertEqual(earnings_data[0]["source"], "finnhub")

        # Note: Refactored service testing is handled by the service adapter
        # which gracefully switches between old and new implementations

    def test_financial_data_flow_with_fallbacks(self):
        """Test the financial data flow with fallbacks when data is not in DB"""
        symbol = "EMPTY"

        # Mock the ETL pipeline to do nothing
        mock_etl = mock.patch("etl.financials_etl.run_financials_etl_pipeline")
        mock_etl.start()

        # Mock Yahoo Finance API to return test data
        yahoo_data = {
            "quarterly_financials": {
                "data": [
                    {
                        "symbol": symbol,
                        "year": 2025,
                        "quarter": 2,
                        "report_type": "quarterly",
                        "filed": "2025-06-30",
                        "report": {
                            "ic": [
                                {"concept": "Revenue", "value": 1500000},
                                {"concept": "Net Income", "value": 150000},
                            ]
                        },
                    }
                ]
            },
            "annual_financials": {"data": []},
            "quarterly_earnings": [],
            "annual_earnings": [],
        }

        with mock.patch(
            "services.alternative_financials.fetch_yahoo_financials",
            return_value=yahoo_data,
        ):
            # Test the original financials service with fallback
            with mock.patch("models.db_models.SessionLocal", return_value=self.session):
                # This should try DB, ETL, then Yahoo Finance
                financials_data = FinancialsService.fetch_financials(symbol)

                # Verify we got data from Yahoo fallback
                self.assertIsNotNone(financials_data)
                self.assertEqual(financials_data["source"], "yahoo_finance")
                self.assertEqual(len(financials_data["data"]), 1)

        mock_etl.stop()

    def test_end_to_end_data_integration(self):
        """
        Test the end-to-end integration of financial data in the system.
        This simulates a complete user interaction flow.
        """
        symbol = "FLOW"

        # 1. First populate stock prices (simulates ETL)
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

        # 2. Add financial data
        financial_report = FinancialReport(
            symbol=symbol,
            report_type="quarterly",
            year=2025,
            quarter=2,
            report_data={
                "ic": [
                    {"concept": "Revenue", "value": 1500000},
                    {"concept": "Net Income", "value": 150000},
                ]
            },
            filing_date=datetime.now() - timedelta(days=30),
            fetched_at=datetime.now(),
        )
        self.session.add(financial_report)

        # 3. Add news data
        news = NewsArticle(
            symbol=symbol,
            headline="Test Company Reports Strong Earnings",
            summary="Test Company (FLOW) reported earnings above expectations.",
            url="https://example.com/news",
            datetime=datetime.now() - timedelta(days=5),
            sentiment=0.8,
        )
        self.session.add(news)

        self.session.commit()

        # 4. Now simulate retrieving all data for the dashboard
        with mock.patch("models.db_models.SessionLocal", return_value=self.session):
            # Get financials
            financials = FinancialsService.fetch_financials(symbol)
            self.assertIsNotNone(financials)

            # Get earnings (will use fallback since we didn't add earnings)
            with mock.patch(
                "services.alternative_financials.fetch_yahoo_financials",
                return_value={"quarterly_earnings": [{"actual": 1.2, "estimate": 1.0}]},
            ):
                earnings = EarningsService.fetch_earnings(symbol)
                self.assertIsNotNone(earnings)

            # Verify the integration of different data types
            self.assertEqual(financials["data"][0]["year"], 2025)
            self.assertEqual(financials["data"][0]["quarter"], 2)

    @mock.patch("requests.get")
    def test_api_error_handling(self, mock_get):
        """Test that API errors are handled gracefully in the integration flow"""
        mock_get.side_effect = Exception("API Error")

        symbol = "ERROR"

        with mock.patch("models.db_models.SessionLocal", return_value=self.session):
            # This should try DB, ETL, Yahoo, then hardcoded, then legacy API (which will fail)
            financials = FinancialsService.fetch_financials(symbol)

            # Despite the error, we should get a valid response structure
            self.assertIsNotNone(financials)
            self.assertIn("data", financials)
            self.assertEqual(len(financials["data"]), 0)
            self.assertIn("error", financials)


if __name__ == "__main__":
    unittest.main()
