"""
Tests for utils.constants module
"""

import pytest

from utils.constants import CacheTTL


class TestCacheTTL:
    """Test cache TTL constants"""

    def test_basic_time_units(self):
        """Test that basic time units are correctly defined"""
        assert CacheTTL.MINUTE == 60
        assert CacheTTL.HOUR == 3600
        assert CacheTTL.DAY == 86400

    def test_cache_values_are_positive(self):
        """Test that all cache values are positive"""
        assert CacheTTL.NEWS_CACHE > 0
        assert CacheTTL.FINANCIALS_CACHE > 0
        assert CacheTTL.FINANCIALS_MAX_CACHE > 0
        assert CacheTTL.EARNINGS_CACHE > 0
        assert CacheTTL.EARNINGS_MAX_CACHE > 0
        assert CacheTTL.ERROR_CACHE > 0

    def test_cache_hierarchy(self):
        """Test that max cache values are greater than or equal to base cache values"""
        assert CacheTTL.FINANCIALS_MAX_CACHE >= CacheTTL.FINANCIALS_CACHE
        assert CacheTTL.EARNINGS_MAX_CACHE >= CacheTTL.EARNINGS_CACHE
        assert CacheTTL.YAHOO_FINANCE_MAX_CACHE >= CacheTTL.YAHOO_FINANCE_CACHE

    def test_error_cache_is_shorter(self):
        """Test that error cache has shorter TTL than regular caches"""
        assert CacheTTL.ERROR_CACHE < CacheTTL.NEWS_CACHE
        assert CacheTTL.ERROR_CACHE < CacheTTL.FINANCIALS_CACHE
        assert CacheTTL.ERROR_CACHE < CacheTTL.EARNINGS_CACHE

    def test_constants_are_integers(self):
        """Test that all constants are integers (seconds)"""
        assert isinstance(CacheTTL.MINUTE, int)
        assert isinstance(CacheTTL.HOUR, int)
        assert isinstance(CacheTTL.DAY, int)
        assert isinstance(CacheTTL.NEWS_CACHE, int)
        assert isinstance(CacheTTL.FINANCIALS_CACHE, int)
