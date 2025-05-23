"""
Unit tests for the refactored service classes.
"""

import unittest
from unittest import mock
from datetime import datetime, timedelta

from models.db_models import FinancialReport, Earnings
from services.refactored_financials import FinancialsService
from services.refactored_earnings import EarningsService
from utils.cache import clear_cache


class TestRefactoredServices(unittest.TestCase):
    """Test the refactored service classes that use the base service pattern"""

    def setUp(self):
        """Set up for each test"""
        # Clear the cache before each test
        clear_cache()

    def test_financials_service_query_format(self):
        """Test that the financials service formats data correctly from database records"""
        # Create mock financial reports
        reports = [
            FinancialReport(
                symbol="TEST",
                year=2025,
                quarter=2,
                report_type="quarterly",
                filing_date=datetime.now() - timedelta(days=30),
                report_data={
                    "ic": [
                        {"concept": "Revenue", "value": 1500000},
                        {"concept": "NetIncome", "value": 300000},
                    ]
                },
                revenue=1500000,
                net_income=300000,
                eps=1.5,
            ),
            FinancialReport(
                symbol="TEST",
                year=2025,
                quarter=1,
                report_type="quarterly",
                filing_date=datetime.now() - timedelta(days=120),
                report_data={
                    "ic": [
                        {"concept": "Revenue", "value": 1400000},
                        {"concept": "NetIncome", "value": 280000},
                    ]
                },
                revenue=1400000,
                net_income=280000,
                eps=1.4,
            ),
        ]

        # Call the format method
        result = FinancialsService._format_records(reports)

        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertIn("data", result)
        self.assertEqual(len(result["data"]), 2)
        self.assertEqual(result["data"][0]["year"], 2025)
        self.assertEqual(result["data"][0]["quarter"], 2)
        self.assertEqual(result["source"], "database")

    def test_earnings_service_query_format(self):
        """Test that the earnings service formats data correctly from database records"""
        # Create mock earnings records
        earnings_records = [
            Earnings(
                symbol="TEST",
                period=datetime.now() - timedelta(days=30),
                year=2025,
                quarter=2,
                eps_actual=1.5,
                eps_estimate=1.3,
                eps_surprise=0.2,
                eps_surprise_percent=15.38,
                is_beat=True,
            ),
            Earnings(
                symbol="TEST",
                period=datetime.now() - timedelta(days=120),
                year=2025,
                quarter=1,
                eps_actual=1.4,
                eps_estimate=1.4,
                eps_surprise=0.0,
                eps_surprise_percent=0.0,
                is_beat=False,
            ),
        ]

        # Call the format method
        result = EarningsService._format_records(earnings_records)

        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertIn("data", result)
        self.assertEqual(len(result["data"]), 2)
        self.assertEqual(result["data"][0]["year"], 2025)
        self.assertEqual(result["data"][0]["quarter"], 2)
        self.assertEqual(result["data"][0]["eps_actual"], 1.5)
        self.assertEqual(result["data"][0]["is_beat"], True)
        self.assertEqual(result["source"], "database")

    @mock.patch("services.refactored_financials.FinancialsService._query_database")
    def test_financials_service_database_path(self, mock_query):
        """Test the happy path when data is in database"""
        # Setup mock to return data
        mock_report = FinancialReport(
            symbol="TEST",
            year=2025,
            quarter=2,
            report_type="quarterly",
            filing_date=datetime.now(),
            report_data={"ic": [{"concept": "Revenue", "value": 1500000}]},
        )
        mock_query.return_value = [mock_report]

        # Create a mock session
        mock_session = mock.MagicMock()

        # Call the method
        result = FinancialsService.fetch_data(mock_session, "TEST")

        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertIn("data", result)
        self.assertEqual(len(result["data"]), 1)
        self.assertEqual(result["source"], "database")

        # Verify the query was called correctly
        mock_query.assert_called_once_with(mock_session, "TEST")

    @mock.patch("services.refactored_earnings.EarningsService._query_database")
    def test_earnings_service_database_path(self, mock_query):
        """Test the happy path when data is in database"""
        # Setup mock to return data
        mock_earnings = Earnings(
            symbol="TEST",
            period=datetime.now(),
            year=2025,
            quarter=2,
            eps_actual=1.5,
            eps_estimate=1.3,
        )
        mock_query.return_value = [mock_earnings]

        # Create a mock session
        mock_session = mock.MagicMock()

        # Call the method
        result = EarningsService.fetch_data(mock_session, "TEST")

        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertIn("data", result)
        self.assertEqual(len(result["data"]), 1)
        self.assertEqual(result["source"], "database")

        # Verify the query was called correctly
        mock_query.assert_called_once_with(mock_session, "TEST")

    @mock.patch("services.refactored_financials.FinancialsService._query_database")
    @mock.patch("services.base_service.ETL_EXECUTOR")
    @mock.patch(
        "services.refactored_financials.FinancialsService._try_alternative_sources"
    )
    def test_financials_service_fallback_path(
        self, mock_alternative, mock_executor, mock_query
    ):
        """Test fallback path when data is not in database"""
        # Setup mocks
        mock_query.return_value = []  # No data in database
        mock_future = mock.MagicMock()
        mock_executor.submit.return_value = mock_future
        mock_future.result.side_effect = Exception("ETL error")  # ETL fails

        # Setup fallback data
        mock_alternative.return_value = {
            "data": [{"year": 2025, "quarter": 2}],
            "source": "yahoo_finance",
        }

        # Create a mock session
        mock_session = mock.MagicMock()

        # Call the method
        result = FinancialsService.fetch_data(mock_session, "TEST")

        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertIn("data", result)
        self.assertEqual(result["source"], "yahoo_finance")

        # Verify mocks were called correctly
        mock_query.assert_called_once()
        mock_executor.submit.assert_called_once()
        mock_alternative.assert_called_once()


if __name__ == "__main__":
    unittest.main()
