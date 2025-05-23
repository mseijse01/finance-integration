"""
Application-wide constants for better maintainability.
"""


# Cache TTL Constants (in seconds)
class CacheTTL:
    """Cache Time-To-Live constants"""

    # Base time units
    MINUTE = 60
    HOUR = 3600
    DAY = 86400

    # News cache
    NEWS_CACHE = HOUR  # 1 hour

    # Financial data cache
    FINANCIALS_CACHE = 6 * HOUR  # 6 hours
    FINANCIALS_MAX_CACHE = 12 * HOUR  # 12 hours

    # Earnings cache
    EARNINGS_CACHE = 12 * HOUR  # 12 hours
    EARNINGS_MAX_CACHE = 24 * HOUR  # 24 hours

    # Alternative data sources
    YAHOO_FINANCE_CACHE = 12 * HOUR  # 12 hours
    YAHOO_FINANCE_MAX_CACHE = 2 * DAY  # 2 days

    # Error cache (shorter TTL for errors)
    ERROR_CACHE = 5 * MINUTE  # 5 minutes

    # Default values
    DEFAULT_CACHE = HOUR  # 1 hour default
    DEFAULT_MAX_CACHE = DAY  # 1 day max default
