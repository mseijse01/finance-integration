"""
Unit tests for the service adapter module.
"""

import unittest
from unittest import mock

from services.service_adapter import (
    fetch_financials,
    fetch_earnings,
    fetch_news,
    use_refactored_services,
)


class TestServiceAdapter(unittest.TestCase):
    """Tests for the service adapter that provides compatibility with refactored services"""

    def setUp(self):
        """Set up before each test"""
        # Enable refactored services by default
        use_refactored_services(True)

    def tearDown(self):
        """Clean up after each test"""
        # Reset to default
        use_refactored_services(True)

    def test_service_adapter_structure(self):
        """Test that the service adapter has the expected structure"""
        # Check that the adapter functions have references to both implementations
        self.assertTrue(hasattr(fetch_financials, "old_func"))
        self.assertTrue(hasattr(fetch_financials, "new_func"))
        self.assertTrue(hasattr(fetch_earnings, "old_func"))
        self.assertTrue(hasattr(fetch_earnings, "new_func"))
        self.assertTrue(hasattr(fetch_news, "old_func"))
        self.assertTrue(hasattr(fetch_news, "new_func"))

        # Verify the functions are properly wrapped
        self.assertEqual(fetch_financials.__name__, "fetch_financials")
        self.assertEqual(fetch_earnings.__name__, "fetch_earnings")
        self.assertEqual(fetch_news.__name__, "fetch_company_news")


if __name__ == "__main__":
    unittest.main()
