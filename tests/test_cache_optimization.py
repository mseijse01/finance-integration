import time
import unittest

from utils.cache import (
    RateLimitExceeded,
    adaptive_ttl_cache,
    clear_api_rate_limits,
    clear_cache,
    rate_limited_api,
)


class TestCacheOptimization(unittest.TestCase):
    def setUp(self):
        clear_cache()
        clear_api_rate_limits()
        self.call_counts = {}

    def test_adaptive_ttl_cache(self):
        @adaptive_ttl_cache(base_ttl=2, max_ttl=5, error_ttl=1)
        def cached_function(param):
            if param not in self.call_counts:
                self.call_counts[param] = 0
            self.call_counts[param] += 1

            if param == "error":
                raise ValueError("Test error")
            elif param == "empty":
                return {"data": []}
            elif param == "full":
                return {"data": [1, 2, 3, 4, 5]}
            else:
                return param

        # Test for normal value
        self.assertEqual(cached_function("test"), "test")
        self.assertEqual(cached_function("test"), "test")
        self.assertEqual(
            self.call_counts["test"], 1
        )  # Function should be called only once

        # Test for full data response
        self.assertEqual(cached_function("full"), {"data": [1, 2, 3, 4, 5]})
        self.assertEqual(cached_function("full"), {"data": [1, 2, 3, 4, 5]})
        self.assertEqual(self.call_counts["full"], 1)

        # Test for empty data response
        self.assertEqual(cached_function("empty"), {"data": []})
        self.assertEqual(cached_function("empty"), {"data": []})
        self.assertEqual(self.call_counts["empty"], 1)

        # Test error caching
        with self.assertRaises(ValueError):
            cached_function("error")
        with self.assertRaises(ValueError):
            cached_function("error")
        self.assertEqual(self.call_counts["error"], 1)  # Error should also be cached

        # Test expiration (wait for error_ttl to expire)
        time.sleep(1.1)
        with self.assertRaises(ValueError):
            cached_function("error")
        self.assertEqual(
            self.call_counts["error"], 2
        )  # Count incremented after expiration

    def test_rate_limited_api(self):
        @rate_limited_api(calls_per_minute=2, retry_after=1, max_retries=1)
        def limited_api(param):
            if param not in self.call_counts:
                self.call_counts[param] = 0
            self.call_counts[param] += 1
            return param

        # First two calls should work
        self.assertEqual(limited_api("test"), "test")
        self.assertEqual(limited_api("test"), "test")

        # Third call should be rate limited
        with self.assertRaises(Exception):
            limited_api("test")

        # Different param should work (separate rate limit)
        self.assertEqual(limited_api("other"), "other")

        # Wait for rate limit to expire
        time.sleep(0.1)
        # Should throw an error because retry count is 1 and retry_after is very short
        with self.assertRaises(Exception):
            limited_api("test")


if __name__ == "__main__":
    unittest.main()
