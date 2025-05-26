"""
Integration tests for the ETL pipeline.
Tests the complete flow from extraction to transformation to loading.
"""

import os
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest import mock

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker

from etl.earnings_etl import run_earnings_etl_pipeline

# Import the ETL components
from etl.extraction import extract_financials, extract_stock_data
from etl.financials_etl import run_financials_etl_pipeline
from etl.loading import load_financials, load_stock_data
from etl.main_etl import run_etl_pipeline
from etl.news_etl import run_news_etl_pipeline
from etl.transformation import transform_financials, transform_stock_data
from models.db_models import Base, Earnings, FinancialReport, NewsArticle, StockPrice


class TestETLPipeline(unittest.TestCase):
    """Integration tests for the complete ETL pipeline"""

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
        os.environ["FINNHUB_API_KEY"] = "test_api_key"

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

        # Set up DB session patch
        self.session_patch = mock.patch(
            "models.db_models.SessionLocal", return_value=self.session
        )
        self.mock_db_session = self.session_patch.start()

    def tearDown(self):
        """Clean up after each test"""
        self.session_patch.stop()
        self.session.close()

    @mock.patch("etl.extraction.extract_stock_data")
    @mock.patch("etl.extraction.extract_financials")
    def test_full_etl_pipeline(self, mock_extract_financials, mock_extract_stock_data):
        """Test the complete ETL pipeline with mocked extractors"""
        # Mock the extractors to return test data
        symbol = "ETLTEST"

        # Setup stock data mock
        dates = pd.date_range(end=datetime.now(), periods=30).tolist()
        stock_data = pd.DataFrame(
            {
                "date": dates,
                "open": np.random.uniform(100, 110, size=30),
                "high": np.random.uniform(110, 120, size=30),
                "low": np.random.uniform(90, 100, size=30),
                "close": np.random.uniform(100, 110, size=30),
                "volume": np.random.randint(1000000, 5000000, size=30),
            }
        )
        mock_extract_stock_data.return_value = stock_data

        # Setup financial data mock
        mock_extract_financials.return_value = {
            "symbol": symbol,
            "financials": [
                {
                    "year": 2025,
                    "quarter": 2,
                    "report_type": "quarterly",
                    "filing_date": "2025-06-30",
                    "report": {
                        "ic": [
                            {"concept": "Revenue", "value": 1500000},
                            {"concept": "CostOfRevenue", "value": 900000},
                            {"concept": "GrossProfit", "value": 600000},
                            {"concept": "NetIncome", "value": 300000},
                        ],
                        "bs": [
                            {"concept": "TotalAssets", "value": 10000000},
                            {"concept": "TotalLiabilities", "value": 5000000},
                        ],
                    },
                }
            ],
        }

        # Run the full ETL pipeline
        run_etl_pipeline(symbol=symbol)

        # Verify that data was loaded into the database
        stock_prices = (
            self.session.query(StockPrice).filter(StockPrice.symbol == symbol).all()
        )
        self.assertEqual(len(stock_prices), 30)

        financial_reports = (
            self.session.query(FinancialReport)
            .filter(FinancialReport.symbol == symbol)
            .all()
        )
        self.assertGreaterEqual(len(financial_reports), 1)

    @mock.patch("requests.get")
    def test_financials_etl_pipeline(self, mock_get):
        """Test the financials ETL pipeline with mocked API responses"""
        symbol = "FINTEST"

        # Mock the API response for financials
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "symbol": symbol,
            "data": [
                {
                    "year": 2025,
                    "quarter": 2,
                    "report": {
                        "ic": [
                            {"concept": "Revenue", "value": 1500000},
                            {"concept": "NetIncome", "value": 300000},
                        ]
                    },
                    "form": "10-Q",
                    "filed": "2025-06-30",
                }
            ],
        }
        mock_get.return_value = mock_response

        # Run the financials ETL pipeline
        run_financials_etl_pipeline(symbol)

        # Verify data in database
        financials = (
            self.session.query(FinancialReport)
            .filter(FinancialReport.symbol == symbol)
            .all()
        )
        self.assertEqual(len(financials), 1)
        self.assertEqual(financials[0].symbol, symbol)
        self.assertEqual(financials[0].year, 2025)
        self.assertEqual(financials[0].quarter, 2)

    @mock.patch("requests.get")
    def test_earnings_etl_pipeline(self, mock_get):
        """Test the earnings ETL pipeline with mocked API responses"""
        symbol = "EARNTEST"

        # Mock the API response for earnings
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "symbol": symbol,
            "data": [
                {
                    "actual": 1.5,
                    "estimate": 1.3,
                    "surprise": 0.2,
                    "surprisePercent": 15.38,
                    "period": "2025-06-30",
                    "year": 2025,
                    "quarter": 2,
                }
            ],
        }
        mock_get.return_value = mock_response

        # Run the earnings ETL pipeline
        run_earnings_etl_pipeline(symbol)

        # Verify data in database
        earnings = self.session.query(Earnings).filter(Earnings.symbol == symbol).all()
        self.assertEqual(len(earnings), 1)
        self.assertEqual(earnings[0].symbol, symbol)
        self.assertEqual(earnings[0].year, 2025)
        self.assertEqual(earnings[0].quarter, 2)
        self.assertEqual(earnings[0].eps_actual, 1.5)

    @mock.patch("requests.get")
    def test_multi_source_integration(self, mock_get):
        """Test that the ETL process can integrate data from multiple sources"""
        symbol = "MULTI"

        def mock_api_call(*args, **kwargs):
            """Mock API responses based on URL"""
            url = args[0] if args else kwargs.get("url", "")

            mock_response = mock.Mock()
            mock_response.status_code = 200

            if "stock/profile2" in url:
                # Company profile
                mock_response.json.return_value = {
                    "name": "Multi Test Inc.",
                    "ticker": symbol,
                    "exchange": "NASDAQ",
                    "industry": "Software",
                }
            elif "stock/candle" in url:
                # Stock price data
                mock_response.json.return_value = {
                    "c": [101.1, 102.2, 103.3],
                    "h": [105.1, 106.2, 107.3],
                    "l": [99.1, 98.2, 97.3],
                    "o": [100.1, 100.2, 100.3],
                    "v": [1000000, 1100000, 1200000],
                    "t": [1625097600, 1625184000, 1625270400],
                    "s": "ok",
                }
            elif "company-news" in url:
                # News data
                mock_response.json.return_value = [
                    {
                        "headline": "Test News 1",
                        "summary": "Test summary 1",
                        "url": "https://example.com/news/1",
                        "datetime": 1625097600,
                    }
                ]
            elif "stock/financials-reported" in url:
                # Financial data
                mock_response.json.return_value = {
                    "data": [
                        {
                            "year": 2025,
                            "quarter": 2,
                            "report": {
                                "ic": [{"concept": "Revenue", "value": 1500000}]
                            },
                            "form": "10-Q",
                            "filed": "2025-06-30",
                        }
                    ]
                }
            elif "stock/earnings" in url:
                # Earnings data
                mock_response.json.return_value = {
                    "data": [
                        {
                            "actual": 1.5,
                            "estimate": 1.3,
                            "period": "2025-06-30",
                            "quarter": 2,
                            "year": 2025,
                        }
                    ]
                }
            else:
                mock_response.json.return_value = {}

            return mock_response

        mock_get.side_effect = mock_api_call

        # Run the complete ETL pipeline with all sources
        run_etl_pipeline(symbol)
        run_financials_etl_pipeline(symbol)
        run_earnings_etl_pipeline(symbol)
        run_news_etl_pipeline(symbol)

        # Verify data from all sources is in the database
        stock_prices = (
            self.session.query(StockPrice).filter(StockPrice.symbol == symbol).all()
        )
        self.assertGreater(len(stock_prices), 0)

        financials = (
            self.session.query(FinancialReport)
            .filter(FinancialReport.symbol == symbol)
            .all()
        )
        self.assertGreater(len(financials), 0)

        earnings = self.session.query(Earnings).filter(Earnings.symbol == symbol).all()
        self.assertGreater(len(earnings), 0)

        news = (
            self.session.query(NewsArticle).filter(NewsArticle.symbol == symbol).all()
        )
        self.assertGreater(len(news), 0)

    @mock.patch("etl.extraction.extract_stock_data")
    def test_incremental_updates(self, mock_extract_stock_data):
        """Test that ETL process performs incremental updates correctly"""
        symbol = "INCR"

        # First add some existing data to the database
        old_date = datetime.now() - timedelta(days=30)
        old_price = StockPrice(
            symbol=symbol,
            date=old_date,
            open=100.0,
            high=105.0,
            low=95.0,
            close=101.0,
            volume=1000000,
        )
        self.session.add(old_price)
        self.session.commit()

        # Setup mock for new data (includes one overlap with the existing data)
        dates = [
            old_date,  # Overlapping date
            datetime.now() - timedelta(days=2),
            datetime.now() - timedelta(days=1),
            datetime.now(),
        ]
        new_data = pd.DataFrame(
            {
                "date": dates,
                "open": [100.5, 101.0, 102.0, 103.0],  # Updated value for existing date
                "high": [105.5, 106.0, 107.0, 108.0],
                "low": [95.5, 96.0, 97.0, 98.0],
                "close": [101.5, 102.0, 103.0, 104.0],
                "volume": [1100000, 1200000, 1300000, 1400000],
            }
        )
        mock_extract_stock_data.return_value = new_data

        # Run the ETL pipeline for stock prices
        run_etl_pipeline(symbol)

        # Verify that we now have 4 records (not 5, as the overlap should update)
        stock_prices = (
            self.session.query(StockPrice)
            .filter(StockPrice.symbol == symbol)
            .order_by(StockPrice.date)
            .all()
        )

        self.assertEqual(len(stock_prices), 4)

        # Verify the overlapping record was updated
        first_record = stock_prices[0]
        self.assertEqual(first_record.date.date(), old_date.date())
        self.assertEqual(first_record.open, 100.5)  # Should have the updated value

    @mock.patch("etl.extraction.extract_financials")
    def test_etl_error_handling(self, mock_extract_financials):
        """Test that the ETL pipeline handles errors gracefully"""
        symbol = "ERROR"

        # Mock extractor to raise an exception
        mock_extract_financials.side_effect = Exception("Test extraction error")

        try:
            # This should not raise an exception to the test
            run_financials_etl_pipeline(symbol)

            # Verify no data was loaded (graceful failure)
            financials = (
                self.session.query(FinancialReport)
                .filter(FinancialReport.symbol == symbol)
                .all()
            )
            self.assertEqual(len(financials), 0)
        except Exception as e:
            self.fail(f"ETL pipeline did not handle error gracefully: {e}")


if __name__ == "__main__":
    unittest.main()
