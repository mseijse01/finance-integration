"""
Simple caching utility for API responses and database queries
to reduce load times on the dashboard.
"""

import time
import functools
from datetime import datetime, timedelta

# In-memory cache storage
_cache = {}


def timed_cache(expire_seconds=3600):
    """
    Decorator that caches function results for a specified time.

    Args:
        expire_seconds: Number of seconds before cache entry expires
                       (default: 1 hour)
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create a cache key from function name and arguments
            key = f"{func.__name__}:{str(args)}:{str(kwargs)}"

            # Check if we have a non-expired cached result
            if key in _cache:
                result, timestamp = _cache[key]
                if time.time() - timestamp < expire_seconds:
                    return result

            # Execute the function and cache the result
            result = func(*args, **kwargs)
            _cache[key] = (result, time.time())
            return result

        return wrapper

    return decorator


def clear_cache():
    """Clear all cached data."""
    global _cache
    _cache = {}


def get_cache_stats():
    """Return statistics about the cache"""
    return {
        "entries": len(_cache),
        "size_estimate": len(str(_cache)),
        "oldest_entry": min([t for _, t in _cache.values()]) if _cache else None,
        "newest_entry": max([t for _, t in _cache.values()]) if _cache else None,
    }
