"""
Enhanced caching utility for API responses and database queries
with rate limiting and exponential backoff strategies.
"""

import builtins
import functools
import random
import time
from datetime import datetime, timedelta
from threading import RLock

# In-memory cache storage
_cache = {}
_rate_limits = {}
_lock = RLock()  # Thread-safe operations


class RateLimitExceeded(Exception):
    """Exception raised when rate limits are exceeded"""

    pass


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

            with _lock:
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


def rate_limited_api(calls_per_minute=5, retry_after=60, max_retries=3):
    """
    Decorator that applies rate limiting and backoff to API calls.

    Args:
        calls_per_minute: Maximum number of calls allowed per minute
        retry_after: Base seconds to wait before retrying
        max_retries: Maximum number of retry attempts
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            endpoint = func.__name__

            # For Yahoo Finance, use the symbol as part of the rate limit key
            if args and isinstance(args[0], str):
                api_key = f"{endpoint}:{args[0]}"
            else:
                api_key = endpoint

            with _lock:
                # Initialize rate limiting data if not exists
                if api_key not in _rate_limits:
                    _rate_limits[api_key] = {
                        "last_reset": time.time(),
                        "calls": 0,
                    }

                # Reset counter if minute has elapsed
                now = time.time()
                if now - _rate_limits[api_key]["last_reset"] > 60:
                    _rate_limits[api_key]["last_reset"] = now
                    _rate_limits[api_key]["calls"] = 0

                # Check if we're over the rate limit
                if _rate_limits[api_key]["calls"] >= calls_per_minute:
                    # Don't increment the counter - we're just checking
                    wait_time = 60 - (now - _rate_limits[api_key]["last_reset"])
                    raise RateLimitExceeded(
                        f"Rate limit exceeded for {api_key}, retry after {wait_time:.1f} seconds"
                    )

                # Increment the counter
                _rate_limits[api_key]["calls"] += 1

            # Try the API call with exponential backoff
            retry_count = 0
            last_error = None

            while retry_count <= max_retries:
                try:
                    result = func(*args, **kwargs)
                    return result
                except RateLimitExceeded as e:
                    last_error = e
                    # Calculate backoff time (exponential with jitter)
                    backoff = retry_after * (2**retry_count) + random.uniform(0, 3)
                    time.sleep(backoff)
                    retry_count += 1
                except Exception as e:
                    # For non-rate limit errors, just retry with backoff
                    last_error = e
                    backoff = retry_after * (2**retry_count) + random.uniform(0, 3)
                    time.sleep(backoff)
                    retry_count += 1

            # If we get here, we've exhausted our retries
            raise last_error or Exception(
                f"Max retries ({max_retries}) exceeded for {api_key}"
            )

        return wrapper

    return decorator


def adaptive_ttl_cache(base_ttl=3600, max_ttl=86400, error_ttl=300):
    """
    Advanced caching with adaptive TTL based on data freshness and error states.

    Args:
        base_ttl: Base TTL for regular responses (1 hour default)
        max_ttl: Maximum TTL for responses that rarely change (24 hours)
        error_ttl: Short TTL for error responses (5 minutes)
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create a cache key from function name and arguments
            key = f"{func.__name__}:{str(args)}:{str(kwargs)}"

            with _lock:
                # Check if we have a cached result
                if key in _cache:
                    result, timestamp, ttl = _cache[key]
                    if time.time() - timestamp < ttl:
                        # Check if this is a cached error result
                        if (
                            isinstance(result, dict)
                            and "error" in result
                            and "error_type" in result
                        ):
                            # Re-raise the original exception type if possible
                            error_type = result.get("error_type")
                            error_msg = result.get("error", "Cached error")
                            # Try to get the exception class from builtins
                            try:
                                exception_class = getattr(builtins, error_type)
                                if issubclass(exception_class, Exception):
                                    raise exception_class(error_msg)
                            except (AttributeError, TypeError):
                                # If we can't get the original exception class, use a generic one
                                raise Exception(f"{error_type}: {error_msg}")
                        return result

                # Execute the function
                try:
                    result = func(*args, **kwargs)

                    # Determine appropriate TTL based on result quality
                    if result is None or (
                        isinstance(result, dict) and result.get("error")
                    ):
                        # For error responses, use short TTL
                        ttl = error_ttl
                    elif isinstance(result, dict):
                        # For empty data or minimal results, use shorter TTL
                        if not result.get("data") or len(result.get("data", [])) == 0:
                            ttl = base_ttl // 2
                        else:
                            # For good data, use normal or extended TTL
                            # Check how old the newest data point is
                            if isinstance(result.get("data"), list) and result["data"]:
                                # For financial data that doesn't change often, use longer TTL
                                ttl = max_ttl
                            else:
                                ttl = base_ttl
                    else:
                        ttl = base_ttl

                    _cache[key] = (result, time.time(), ttl)
                    return result

                except Exception as e:
                    # If an error occurs, cache the error for a short time
                    error_result = {
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "is_cached_error": True,
                    }
                    _cache[key] = (error_result, time.time(), error_ttl)
                    raise

        return wrapper

    return decorator


def clear_cache():
    """Clear all cached data."""
    with _lock:
        global _cache
        _cache = {}


def clear_api_rate_limits():
    """Reset all API rate limit counters."""
    with _lock:
        global _rate_limits
        _rate_limits = {}


def get_cache_stats():
    """Return statistics about the cache"""
    with _lock:
        stats = {
            "entries": len(_cache),
            "size_estimate": len(str(_cache)),
            "rate_limited_apis": len(_rate_limits),
            "oldest_entry": None,
            "newest_entry": None,
        }

        if _cache:
            oldest = min([t for _, t, _ in _cache.values()]) if _cache else None
            newest = max([t for _, t, _ in _cache.values()]) if _cache else None
            stats["oldest_entry"] = (
                datetime.fromtimestamp(oldest).isoformat() if oldest else None
            )
            stats["newest_entry"] = (
                datetime.fromtimestamp(newest).isoformat() if newest else None
            )

        return stats
