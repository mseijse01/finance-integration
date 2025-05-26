"""
Service adapter module that provides backwards compatibility
for refactored services with the existing view code.
"""

import functools
from typing import Any, Callable, Dict, List, Union

from services.earnings import fetch_earnings as old_fetch_earnings
# Import both old and new service implementations
from services.financials import fetch_financials as old_fetch_financials
from services.refactored_earnings import EarningsService
from services.refactored_financials import FinancialsService
from utils.logging_config import logger

# Feature toggle to enable/disable refactored services
USE_REFACTORED_SERVICES = True


def with_fallback(old_func: Callable, new_func: Callable) -> Callable:
    """
    Decorator that provides fallback to old implementation
    if the new one fails.

    Args:
        old_func: The original function to use as fallback
        new_func: The new implementation to try first

    Returns:
        A wrapped function that tries the new implementation first,
        falling back to the old one if it fails.
    """

    @functools.wraps(old_func)
    def wrapper(*args, **kwargs):
        if not USE_REFACTORED_SERVICES:
            return old_func(*args, **kwargs)

        symbol = args[0] if args else kwargs.get("symbol")
        if not symbol:
            logger.warning(
                "No symbol provided to service, falling back to old implementation"
            )
            return old_func(*args, **kwargs)

        try:
            # Try the new implementation first
            return new_func(*args, **kwargs)
        except Exception as e:
            logger.warning(
                f"Error using refactored service for {symbol}: {e}, "
                f"falling back to old implementation"
            )
            return old_func(*args, **kwargs)

    # Store references to both implementations for testing/introspection
    wrapper.old_func = old_func
    wrapper.new_func = new_func

    return wrapper


# Create the adapted service functions
fetch_financials = with_fallback(
    old_fetch_financials, FinancialsService.fetch_financials
)

fetch_earnings = with_fallback(old_fetch_earnings, EarningsService.fetch_earnings)


# Function to completely switch to refactored implementations
def use_refactored_services(enabled: bool = True) -> None:
    """
    Enable or disable the use of refactored services.

    Args:
        enabled: If True, use refactored services. If False, use old services.
    """
    global USE_REFACTORED_SERVICES
    USE_REFACTORED_SERVICES = enabled
    logger.info(f"{'Enabled' if enabled else 'Disabled'} refactored services")
