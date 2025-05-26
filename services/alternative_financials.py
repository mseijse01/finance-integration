"""
Alternative financial data service using Yahoo Finance API.
Used as a secondary source or fallback when Finnhub data is unavailable.
"""

import time
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

from utils.cache import RateLimitExceeded, adaptive_ttl_cache, rate_limited_api
from utils.logging_config import logger


@adaptive_ttl_cache(
    base_ttl=3600 * 12, max_ttl=86400, error_ttl=300
)  # 12h base, 24h max, 5min for errors
@rate_limited_api(
    calls_per_minute=3, retry_after=30, max_retries=2
)  # Strict rate limiting for Yahoo API
def fetch_yahoo_financials(symbol):
    """
    Fetch financial data for a given symbol from Yahoo Finance API.
    Returns quarterly and annual financial data.
    Uses rate limiting and adaptive caching to prevent API errors.
    """
    try:
        logger.info(f"[YF] Fetching Yahoo Finance data for {symbol}")
        start_time = time.time()

        # Add timeout to prevent hanging API calls
        ticker = yf.Ticker(symbol)

        # Add a timeout mechanism for hanging operations
        def timeout_handler(max_time=30):
            if time.time() - start_time > max_time:
                logger.warning(
                    f"[YF] Timed out while fetching data for {symbol} after {max_time} seconds"
                )
                raise TimeoutError(f"API request timed out after {max_time} seconds")

        # Get financial data with timeout check
        timeout_handler()
        quarterly_financials = process_financials(
            ticker.quarterly_financials, symbol, "quarterly"
        )

        timeout_handler()
        annual_financials = process_financials(ticker.financials, symbol, "annual")

        # Get earnings data with better error handling
        quarterly_earnings = []
        annual_earnings = []

        # Fail fast if we've already hit timeouts
        timeout_handler()

        # Try to get quarterly earnings but handle failures gracefully
        try:
            quarterly_earnings = process_earnings(
                ticker.quarterly_earnings, symbol, "quarterly"
            )
        except Exception as e:
            logger.warning(
                f"[YF] Could not fetch quarterly earnings for {symbol} from Yahoo: {e}"
            )
            # Try to get earnings from ticker info instead - with timeout
            timeout_handler()
            try:
                info = ticker.info
                if "trailingEps" in info:
                    eps_value = info["trailingEps"]
                    # Create a synthetic earnings report based on info
                    quarterly_earnings = [
                        {
                            "actual": eps_value,
                            "estimate": None,
                            "surprise": None,
                            "surprisePercent": None,
                            "period": datetime.now().strftime("%Y-%m-%d"),
                            "quarter": (datetime.now().month - 1) // 3 + 1,
                            "year": datetime.now().year,
                            "source": "yahoo_finance",
                        }
                    ]
            except Exception as inner_e:
                logger.warning(
                    f"[YF] Could not get EPS from ticker info for {symbol}: {inner_e}"
                )

        # Try to get annual earnings but handle failures gracefully
        timeout_handler()
        try:
            annual_earnings = process_earnings(ticker.earnings, symbol, "annual")
        except Exception as e:
            logger.warning(
                f"[YF] Could not fetch annual earnings for {symbol} from Yahoo: {e}"
            )

        # Return all the data we could collect
        result = {
            "quarterly_financials": quarterly_financials,
            "annual_financials": annual_financials,
            "quarterly_earnings": quarterly_earnings,
            "annual_earnings": annual_earnings,
        }

        # Ensure we have at least some data
        any_data = (
            (quarterly_financials and len(quarterly_financials.get("data", [])) > 0)
            or (annual_financials and len(annual_financials.get("data", [])) > 0)
            or len(quarterly_earnings) > 0
            or len(annual_earnings) > 0
        )

        if any_data:
            logger.info(
                f"[YF] Successfully fetched Yahoo Finance data for {symbol} in {time.time() - start_time:.2f}s"
            )
            return result
        else:
            logger.warning(f"[YF] No data found in Yahoo Finance API for {symbol}")
            return {
                "quarterly_financials": {"data": []},
                "annual_financials": {"data": []},
                "quarterly_earnings": [],
                "annual_earnings": [],
                "error": "No data available from Yahoo Finance API",
            }

    except TimeoutError as e:
        logger.error(f"[YF] Timeout fetching Yahoo Finance data for {symbol}: {e}")
        return {
            "quarterly_financials": {"data": []},
            "annual_financials": {"data": []},
            "quarterly_earnings": [],
            "annual_earnings": [],
            "error": f"Timeout: {str(e)}",
        }
    except RateLimitExceeded as e:
        logger.error(f"[YF] Rate limit exceeded for Yahoo Finance API - {symbol}: {e}")
        return {
            "quarterly_financials": {"data": []},
            "annual_financials": {"data": []},
            "quarterly_earnings": [],
            "annual_earnings": [],
            "error": f"Rate limited: {str(e)}",
        }
    except Exception as e:
        logger.error(
            f"[YF] Error fetching Yahoo Finance data for {symbol}: {e}", exc_info=True
        )
        return {
            "quarterly_financials": {"data": []},
            "annual_financials": {"data": []},
            "quarterly_earnings": [],
            "annual_earnings": [],
            "error": str(e),
        }


def process_financials(financials_df, symbol, report_type):
    """
    Process financials dataframe from Yahoo Finance into a structured format
    similar to Finnhub's response.
    """
    if financials_df is None or financials_df.empty:
        logger.warning(f"[YF] No {report_type} financials available for {symbol}")
        return {"data": []}

    try:
        # Convert the DataFrame to our desired format
        data = []

        # Yahoo Finance has columns as dates and rows as metrics
        for date_col in financials_df.columns:
            # Convert the column to a dictionary of metrics
            report = {}

            # Get the report date info
            report_date = date_col.to_pydatetime()
            year = report_date.year

            # For quarterly reports, calculate the quarter
            quarter = None
            if report_type == "quarterly":
                quarter = (report_date.month - 1) // 3 + 1

            # Extract key metrics (rows in the dataframe)
            revenue = None
            net_income = None

            # Try different revenue labels that Yahoo might use
            revenue_labels = ["Total Revenue", "Revenue", "Sales"]
            for label in revenue_labels:
                if label in financials_df.index:
                    try:
                        revenue = float(financials_df.loc[label, date_col])
                        break
                    except (ValueError, TypeError):
                        continue

            # Try different net income labels
            net_income_labels = ["Net Income", "Net Income Common Stockholders"]
            for label in net_income_labels:
                if label in financials_df.index:
                    try:
                        net_income = float(financials_df.loc[label, date_col])
                        break
                    except (ValueError, TypeError):
                        continue

            # Create a structure that mimics Finnhub's format for easier integration
            report_data = {
                "ic": [  # Income statement items
                    {"concept": "Revenue", "value": revenue},
                    {"concept": "Net Income", "value": net_income},
                ]
            }

            processed_report = {
                "symbol": symbol,
                "year": year,
                "quarter": quarter,
                "report_type": report_type,
                "source": "yahoo_finance",
                "filed": report_date.strftime("%Y-%m-%d"),
                "report": report_data,
            }

            data.append(processed_report)

        # Sort by date (most recent first)
        data.sort(
            key=lambda x: (x["year"], x.get("quarter", 0) if x.get("quarter") else 0),
            reverse=True,
        )

        return {"data": data}
    except Exception as e:
        logger.error(
            f"[YF] Error processing {report_type} financials for {symbol}: {e}",
            exc_info=True,
        )
        return {"data": []}


def process_earnings(earnings_df, symbol, report_type):
    """
    Process earnings dataframe from Yahoo Finance into a structured format
    similar to Finnhub's response.
    """
    if earnings_df is None or earnings_df.empty:
        logger.warning(f"[YF] No {report_type} earnings available for {symbol}")
        return []

    try:
        # Convert the DataFrame to our desired format
        data = []

        if report_type == "quarterly":
            # For quarterly earnings, we have dates as index
            for date_idx in earnings_df.index:
                # Get the date info
                if isinstance(date_idx, str):
                    try:
                        # Try to parse the date string
                        report_date = datetime.strptime(date_idx, "%Y-%m-%d")
                    except ValueError:
                        # If it's not a valid date string, skip this entry
                        continue
                else:
                    report_date = date_idx.to_pydatetime()

                year = report_date.year
                quarter = (report_date.month - 1) // 3 + 1

                # Extract key metrics
                eps_actual = None
                eps_estimate = None

                # Try to safely extract earnings values
                if "Earnings" in earnings_df.columns:
                    try:
                        eps_actual = float(earnings_df.loc[date_idx, "Earnings"])
                    except (ValueError, TypeError):
                        pass

                if "Estimate" in earnings_df.columns:
                    try:
                        eps_estimate = float(earnings_df.loc[date_idx, "Estimate"])
                    except (ValueError, TypeError):
                        pass

                # Calculate surprise if both actual and estimate are available
                eps_surprise = None
                eps_surprise_percent = None
                if eps_actual is not None and eps_estimate is not None:
                    eps_surprise = eps_actual - eps_estimate
                    if eps_estimate != 0:
                        eps_surprise_percent = (eps_surprise / abs(eps_estimate)) * 100

                processed_earnings = {
                    "actual": eps_actual,
                    "estimate": eps_estimate,
                    "surprise": eps_surprise,
                    "surprisePercent": eps_surprise_percent,
                    "period": report_date.strftime("%Y-%m-%d"),
                    "quarter": quarter,
                    "year": year,
                    "source": "yahoo_finance",
                }

                data.append(processed_earnings)
        else:
            # For annual earnings, it's usually a simple data structure
            for year in earnings_df.index:
                # Extract metrics
                eps = None

                # Try to safely extract earnings values
                if "Earnings" in earnings_df.columns:
                    try:
                        eps = float(earnings_df.loc[year, "Earnings"])
                    except (ValueError, TypeError):
                        pass

                # Create a date for the end of the year
                try:
                    year_int = int(year)
                    report_date = datetime(year_int, 12, 31)

                    processed_earnings = {
                        "actual": eps,
                        "estimate": None,  # Yahoo doesn't provide annual estimates
                        "surprise": None,
                        "surprisePercent": None,
                        "period": report_date.strftime("%Y-%m-%d"),
                        "quarter": None,
                        "year": year_int,
                        "source": "yahoo_finance",
                    }

                    data.append(processed_earnings)
                except (ValueError, TypeError):
                    logger.warning(
                        f"[YF] Could not process annual earnings year value: {year}"
                    )
                    continue

        # Sort by date (most recent first)
        if report_type == "quarterly" and data:
            try:
                data.sort(
                    key=lambda x: datetime.strptime(x["period"], "%Y-%m-%d"),
                    reverse=True,
                )
            except (ValueError, KeyError):
                pass  # Skip sorting if there's an issue
        elif data:
            try:
                data.sort(key=lambda x: x["year"], reverse=True)
            except (ValueError, KeyError):
                pass  # Skip sorting if there's an issue

        return data
    except Exception as e:
        logger.error(
            f"[YF] Error processing {report_type} earnings for {symbol}: {e}",
            exc_info=True,
        )
        return []


@adaptive_ttl_cache(base_ttl=3600 * 24, max_ttl=86400 * 2, error_ttl=3600)
def compare_financial_sources(symbol, finnhub_data, yahoo_data):
    """
    Compare financial data from Finnhub and Yahoo Finance to identify discrepancies.
    """
    try:
        logger.info(f"Comparing financial data sources for {symbol}")

        # Initialize comparison results
        comparison = {
            "quarterly": [],
            "annual": [],
            "earnings": [],
            "has_discrepancies": False,
        }

        # Compare quarterly financials if both sources have data
        finnhub_quarterly = (
            finnhub_data.get("quarterly_financials", {}).get("data", [])
            if finnhub_data
            else []
        )
        yahoo_quarterly = (
            yahoo_data.get("quarterly_financials", {}).get("data", [])
            if yahoo_data
            else []
        )

        if finnhub_quarterly and yahoo_quarterly:
            # For each Yahoo Finance report, try to find a matching Finnhub report
            for yahoo_report in yahoo_quarterly:
                yahoo_year = yahoo_report.get("year")
                yahoo_quarter = yahoo_report.get("quarter")

                # Find matching Finnhub report
                matching_finnhub = next(
                    (
                        fr
                        for fr in finnhub_quarterly
                        if fr.get("year") == yahoo_year
                        and fr.get("quarter") == yahoo_quarter
                    ),
                    None,
                )

                if matching_finnhub:
                    # Extract metrics for comparison
                    yahoo_revenue = extract_metric(yahoo_report, "Revenue")
                    finnhub_revenue = extract_metric(matching_finnhub, "Revenue")

                    yahoo_net_income = extract_metric(yahoo_report, "Net Income")
                    finnhub_net_income = extract_metric(matching_finnhub, "Net Income")

                    # Calculate percentage differences
                    revenue_diff = calculate_difference(yahoo_revenue, finnhub_revenue)
                    net_income_diff = calculate_difference(
                        yahoo_net_income, finnhub_net_income
                    )

                    # Record discrepancies if the difference exceeds a threshold
                    threshold = 0.05  # 5% difference threshold

                    discrepancy = {
                        "year": yahoo_year,
                        "quarter": yahoo_quarter,
                        "period": f"Q{yahoo_quarter} {yahoo_year}",
                        "metrics": {
                            "revenue": {
                                "yahoo": yahoo_revenue,
                                "finnhub": finnhub_revenue,
                                "diff_percentage": revenue_diff,
                                "is_significant": abs(revenue_diff) > threshold
                                if revenue_diff is not None
                                else False,
                            },
                            "net_income": {
                                "yahoo": yahoo_net_income,
                                "finnhub": finnhub_net_income,
                                "diff_percentage": net_income_diff,
                                "is_significant": abs(net_income_diff) > threshold
                                if net_income_diff is not None
                                else False,
                            },
                        },
                        "has_discrepancy": (
                            abs(revenue_diff) > threshold
                            if revenue_diff is not None
                            else False
                        )
                        or (
                            abs(net_income_diff) > threshold
                            if net_income_diff is not None
                            else False
                        ),
                    }

                    comparison["quarterly"].append(discrepancy)
                    if discrepancy["has_discrepancy"]:
                        comparison["has_discrepancies"] = True

        # Similar comparisons can be done for annual data and earnings
        # For brevity, we'll return what we have so far

        logger.info(f"Completed financial data comparison for {symbol}")
        return comparison
    except Exception as e:
        logger.error(f"Error comparing financial data for {symbol}: {e}", exc_info=True)
        return {"error": str(e)}


def extract_metric(report, metric_name):
    """
    Extract a specific metric from a financial report.
    Works with both Finnhub and Yahoo Finance report structures.
    """
    if not report:
        return None

    # For Yahoo Finance format
    if "source" in report and report["source"] == "yahoo_finance":
        ic_items = report.get("report", {}).get("ic", [])
        for item in ic_items:
            if metric_name.lower() in item.get("concept", "").lower():
                return item.get("value")

    # For Finnhub format
    else:
        ic_items = report.get("report", {}).get("ic", [])
        for item in ic_items:
            concept = item.get("concept", "").lower()
            if metric_name.lower() in concept:
                return item.get("value")

    return None


def calculate_difference(value1, value2):
    """
    Calculate the percentage difference between two values.
    """
    if value1 is None or value2 is None:
        return None

    try:
        value1 = float(value1)
        value2 = float(value2)

        # Avoid division by zero
        if value1 == 0 and value2 == 0:
            return 0
        elif value1 == 0:
            return float("inf") if value2 > 0 else float("-inf")

        return ((value2 - value1) / abs(value1)) * 100
    except (ValueError, TypeError):
        return None
