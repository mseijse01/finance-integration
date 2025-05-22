from flask import Blueprint, render_template, Response, request, g
import pandas as pd
import polars as pl
from plotly.subplots import make_subplots
import plotly.graph_objs as go
import plotly.io as pio
from datetime import datetime, timedelta
import io
import csv
from models.db_models import (
    SessionLocal,
    StockPrice,
    NewsArticle,
    FinancialReport,
    Earnings,
)
from utils.logging_config import logger
from etl.extraction import fetch_stock_data
from etl.transformation import transform_stock_data
import threading
from utils.cache import timed_cache, clear_cache, get_cache_stats
import numpy as np
from sqlalchemy import desc
import time

dashboard_bp = Blueprint("dashboard", __name__)


# Define the background data loading mechanism
def load_stock_data_background():
    """Load all stock data in the background to warm up cache"""
    # We need to import these functions inside the thread to avoid circular imports
    # and ensure the functions are defined before being called
    from views.dashboard import (
        get_news_from_db,
        get_financials_from_db,
        get_earnings_from_db,
    )

    cannabis_stocks = ["CGC", "ACB", "CRON", "TLRY"]
    for symbol in cannabis_stocks:
        try:
            get_news_from_db(symbol)
            get_financials_from_db(symbol)
            get_earnings_from_db(symbol)
        except Exception as e:
            logger.error(f"Error preloading data for {symbol}: {e}")


# Start background data loading on module import
# Delay the thread start to ensure all functions are defined
def start_background_loading():
    time.sleep(2)  # Wait 2 seconds to ensure all functions are defined
    threading.Thread(target=load_stock_data_background, daemon=True).start()


# Schedule the background loading to start after a delay
threading.Thread(target=start_background_loading, daemon=True).start()


@timed_cache(expire_seconds=300)  # Cache DB results for 5 minutes
def get_stock_price_data(symbol, days=180):
    """
    Get stock price data from database with caching and data reduction.
    Limits data to specified number of days and applies downsampling for longer periods.
    """
    session = SessionLocal()
    try:
        # Get data for only the last X days to reduce chart load time
        date_cutoff = (datetime.now() - timedelta(days=days)).date()

        query = (
            session.query(StockPrice)
            .filter(StockPrice.symbol == symbol, StockPrice.date >= date_cutoff)
            .order_by(StockPrice.date.asc())
        )
        records = [r.__dict__ for r in query]
        for r in records:
            r.pop("_sa_instance_state", None)

        # Apply downsampling if we have lots of data points
        if len(records) > 100:
            return downsample_data(records)
        return records
    finally:
        session.close()


@timed_cache(expire_seconds=300)  # Cache DB results for 5 minutes
def get_news_from_db(symbol, limit=10):
    """
    Get news articles from database.
    """
    session = SessionLocal()
    try:
        logger.info(f"Getting news from database for {symbol}")
        query = (
            session.query(NewsArticle)
            .filter(NewsArticle.symbol == symbol)
            .order_by(desc(NewsArticle.datetime))
            .limit(limit)
        )
        news_records = query.all()

        if not news_records:
            logger.warning(f"No news found in database for {symbol}")
            return []

        # Convert to dictionary format
        news = []
        for record in news_records:
            news_item = {
                "headline": record.headline,
                "summary": record.summary,
                "url": record.url,
                "source": record.source,
                "datetime": record.datetime.timestamp() if record.datetime else None,
                "sentiment": record.sentiment,
                "category": record.category,
                "related": record.related,
            }
            news.append(news_item)

        logger.info(f"Retrieved {len(news)} news articles from database for {symbol}")
        return news
    except Exception as e:
        logger.error(
            f"Error retrieving news from database for {symbol}: {e}", exc_info=True
        )
        return []
    finally:
        session.close()


@timed_cache(expire_seconds=600)  # Cache DB results for 10 minutes
def get_financials_from_db(symbol, report_type="quarterly", limit=4):
    """
    Get financial reports from database.
    """
    session = SessionLocal()
    try:
        logger.info(f"Getting {report_type} financials from database for {symbol}")
        query = (
            session.query(FinancialReport)
            .filter(
                FinancialReport.symbol == symbol,
                FinancialReport.report_type == report_type,
            )
            .order_by(
                desc(FinancialReport.year),
                desc(FinancialReport.quarter)
                if report_type == "quarterly"
                else desc(FinancialReport.year),
            )
            .limit(limit)
        )
        financial_records = query.all()

        if not financial_records:
            # Fallback to annual if quarterly not found
            if report_type == "quarterly":
                logger.warning(
                    f"No quarterly financials found, trying annual for {symbol}"
                )
                return get_financials_from_db(symbol, "annual", limit)
            else:
                logger.warning(f"No financials found in database for {symbol}")
                return {"data": []}

        # Convert to the format expected by the dashboard
        data = []
        for record in financial_records:
            financial_data = {
                "year": record.year,
                "quarter": record.quarter,
                "report": record.report_data,
                "filing_date": record.filing_date.strftime("%Y-%m-%d")
                if record.filing_date
                else None,
            }
            data.append(financial_data)

        logger.info(
            f"Retrieved {len(data)} financial reports from database for {symbol}"
        )
        return {"data": data}
    except Exception as e:
        logger.error(
            f"Error retrieving financials from database for {symbol}: {e}",
            exc_info=True,
        )
        return {"data": []}
    finally:
        session.close()


@timed_cache(expire_seconds=600)  # Cache DB results for 10 minutes
def get_earnings_from_db(symbol, limit=4):
    """
    Get earnings data from database.
    """
    session = SessionLocal()
    try:
        logger.info(f"Getting earnings from database for {symbol}")
        query = (
            session.query(Earnings)
            .filter(Earnings.symbol == symbol)
            .order_by(desc(Earnings.period))
            .limit(limit)
        )
        earnings_records = query.all()

        if not earnings_records:
            logger.warning(f"No earnings found in database for {symbol}")
            return []

        # Convert to the format expected by the dashboard
        earnings = []
        for record in earnings_records:
            earning_data = {
                "actual": record.eps_actual,
                "estimate": record.eps_estimate,
                "surprise": record.eps_surprise,
                "surprisePercent": record.eps_surprise_percent,
                "period": record.period.strftime("%Y-%m-%d") if record.period else None,
                "quarter": record.quarter,
                "year": record.year,
            }
            earnings.append(earning_data)

        logger.info(
            f"Retrieved {len(earnings)} earnings records from database for {symbol}"
        )
        return earnings
    except Exception as e:
        logger.error(
            f"Error retrieving earnings from database for {symbol}: {e}", exc_info=True
        )
        return []
    finally:
        session.close()


def downsample_data(records, target_points=100):
    """
    Downsample data to approximately target_points to improve chart rendering performance.
    Uses a simple method that preserves important points like min/max values.
    """
    if len(records) <= target_points:
        return records

    # Calculate sampling factor
    sample_factor = max(1, len(records) // target_points)

    # Create sampled data with regular intervals
    sampled = records[::sample_factor]

    # Always include the first and last points
    if records[0] not in sampled:
        sampled.insert(0, records[0])
    if records[-1] not in sampled:
        sampled.append(records[-1])

    # Find extreme values that might be missed in the sampling
    all_values = np.array([r["close"] for r in records])
    min_idx = np.argmin(all_values)
    max_idx = np.argmax(all_values)

    # Add extremes if they're not in the sample
    for idx in [min_idx, max_idx]:
        if idx % sample_factor != 0:  # Not already in our sample
            # Insert at the right position to maintain date order
            insert_pos = 0
            for i, r in enumerate(sampled):
                if r["date"] > records[idx]["date"]:
                    insert_pos = i
                    break
            sampled.insert(insert_pos, records[idx])

    return sampled


@dashboard_bp.route("/")
def dashboard():
    # Use cached DB queries and API calls
    cannabis_stocks = ["CGC", "ACB", "CRON", "TLRY"]

    # Create figure with a subplot for the price chart
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.1,
        row_heights=[0.7, 0.3],
        subplot_titles=("Price History", "Trading Volume"),
    )

    # Colors for different stocks
    colors = {
        "CGC": "#198754",  # Green
        "ACB": "#0d6efd",  # Blue
        "CRON": "#dc3545",  # Red
        "TLRY": "#fd7e14",  # Orange
    }

    # Default visibility for stocks (show only the first one by default to speed up initial rendering)
    default_visibility = {
        "CGC": True,  # Only show the first stock's price trace by default
        "ACB": "legendonly",
        "CRON": "legendonly",
        "TLRY": "legendonly",
    }

    # Get display timeframe from query parameter, default to 6 months
    timeframe = request.args.get("timeframe", "6m")

    # Convert timeframe to days
    days_to_show = {
        "1m": 30,
        "3m": 90,
        "6m": 180,
        "1y": 365,
        "all": 3650,  # ~10 years max
    }.get(timeframe, 180)

    news_sections = {}
    financials_sections = {}

    max_date = None
    min_date = None

    # Use threading to parallelize data loading for each stock
    def process_stock(symbol):
        nonlocal news_sections, financials_sections

        # Get stock price data (cached and optimized for performance)
        records = get_stock_price_data(symbol, days=days_to_show)

        if records:
            df = pl.DataFrame(records).sort("date").to_pandas()

            # Track date range for the current thread's stock
            thread_max_date = df["date"].max()
            thread_min_date = df["date"].min()

            # Synchronize access to shared variables
            with threading.Lock():
                nonlocal max_date, min_date
                if max_date is None or thread_max_date > max_date:
                    max_date = thread_max_date
                if min_date is None or thread_min_date < min_date:
                    min_date = thread_min_date

            # Price chart
            with threading.Lock():
                fig.add_trace(
                    go.Scatter(
                        x=df["date"],
                        y=df["close"],
                        mode="lines",
                        name=f"{symbol} Price",
                        line=dict(color=colors.get(symbol, "#000000"), width=2),
                        hovertemplate="<b>%{x}</b><br>Price: $%{y:.2f}<extra></extra>",
                        visible=default_visibility.get(symbol, True),
                    ),
                    row=1,
                    col=1,
                )

                # Add moving average - always as legendonly to reduce initial load
                fig.add_trace(
                    go.Scatter(
                        x=df["date"],
                        y=df["moving_average_20"],
                        mode="lines",
                        name=f"{symbol} 20-Day MA",
                        line=dict(
                            color=colors.get(symbol, "#000000"), width=1, dash="dash"
                        ),
                        opacity=0.7,
                        visible="legendonly",  # Always hidden by default
                        hovertemplate="<b>%{x}</b><br>MA-20: $%{y:.2f}<extra></extra>",
                    ),
                    row=1,
                    col=1,
                )

                # Volume chart - only for the primary visible stock by default
                fig.add_trace(
                    go.Bar(
                        x=df["date"],
                        y=df["volume"],
                        name=f"{symbol} Volume",
                        marker=dict(color=colors.get(symbol, "#000000"), opacity=0.7),
                        hovertemplate="<b>%{x}</b><br>Volume: %{y:,.0f}<extra></extra>",
                        visible=default_visibility.get(symbol, True),
                    ),
                    row=2,
                    col=1,
                )

        # Get and process news (from DB)
        news = get_news_from_db(symbol)
        news_html = process_news(news, symbol)

        # Get financials and earnings (from DB)
        financials_html = process_financials(symbol)

        # Store results in shared dictionaries
        with threading.Lock():
            news_sections[symbol] = news_html
            financials_sections[symbol] = financials_html

    # Helper function to process news data
    def process_news(news, symbol):
        if news:
            news_html = "<ul class='list-group'>"
            sentiments = []
            for article in news[:5]:
                sentiment = article.get("sentiment", 0)
                sentiments.append(sentiment)

                # Set sentiment icon and class
                if sentiment > 0.3:
                    sentiment_class = "positive"
                    sentiment_icon = "bi-arrow-up-circle-fill"
                elif sentiment > 0:
                    sentiment_class = "neutral"
                    sentiment_icon = "bi-dash-circle-fill"
                else:
                    sentiment_class = "negative"
                    sentiment_icon = "bi-arrow-down-circle-fill"

                news_html += f"""
                    <li class="list-group-item border-0 px-0">
                        <div class="d-flex">
                            <div class="me-2">
                                <i class="bi {sentiment_icon} {sentiment_class}"></i>
                            </div>
                            <div>
                                <div>{article["headline"]}</div>
                                <small class="text-muted">
                                    <a href="{article.get("url", "#")}" target="_blank" class="text-decoration-none">
                                        Read more <i class="bi bi-box-arrow-up-right"></i>
                                    </a>
                                    <span class="ms-2 {sentiment_class}">Sentiment: {sentiment:.2f}</span>
                                </small>
                            </div>
                        </div>
                    </li>
                """
            news_html += "</ul>"
            return {
                "headlines": news_html,
                "average_sentiment": sum(sentiments) / len(sentiments)
                if sentiments
                else None,
            }
        else:
            return {
                "headlines": '<div class="alert alert-light">No recent news available.</div>',
                "average_sentiment": None,
            }

    # Helper function to process financials and earnings data
    def process_financials(symbol):
        financials = get_financials_from_db(symbol, report_type="quarterly")
        if not financials or not financials.get("data"):
            financials = get_financials_from_db(symbol, report_type="annual")

        earnings = get_earnings_from_db(symbol)

        # Process financials
        revenue = net_income = "N/A"
        report_period = "N/A"

        if financials and financials.get("data") and len(financials["data"]) > 0:
            # Get the most recent financial report
            report_data = financials["data"][0]

            # Try to get pre-extracted metrics directly from the database model fields first
            session = SessionLocal()
            try:
                latest_financial = (
                    session.query(FinancialReport)
                    .filter(
                        FinancialReport.symbol == symbol,
                        FinancialReport.year == report_data.get("year"),
                        FinancialReport.quarter == report_data.get("quarter"),
                        FinancialReport.report_type == "quarterly"
                        if report_data.get("quarter")
                        else "annual",
                    )
                    .first()
                )

                if latest_financial:
                    # Use pre-extracted fields from the database model if available
                    if latest_financial.revenue is not None:
                        revenue = latest_financial.revenue
                    if latest_financial.net_income is not None:
                        net_income = latest_financial.net_income
            except Exception as e:
                logger.warning(f"Could not get financial metrics from database: {e}")
            finally:
                session.close()

            # If we still don't have values, try to extract from the report data
            if revenue == "N/A" or net_income == "N/A":
                # Method 1: Extract from report_data using the extract_financial_metric function
                if "report_data" in report_data and report_data["report_data"]:
                    try:
                        # Try to extract from the full report structure
                        full_report = report_data["report_data"]

                        # Try different possible paths to find income statement data
                        if revenue == "N/A":
                            revenue = extract_financial_metric_deep(
                                full_report, ["Revenue", "totalRevenue", "revenues"]
                            )

                        if net_income == "N/A":
                            net_income = extract_financial_metric_deep(
                                full_report, ["Net Income", "netIncome", "net_income"]
                            )
                    except Exception as e:
                        logger.warning(
                            f"Failed to extract metrics from report_data: {e}"
                        )

                # Method 2: Try the original method on the 'report' field if metrics still not found
                if (
                    revenue == "N/A" or net_income == "N/A"
                ) and "report" in report_data:
                    try:
                        report = report_data.get("report", {})

                        if revenue == "N/A":
                            revenue = extract_financial_metric(
                                report, ["Revenue", "totalRevenue", "revenues"]
                            )

                        if net_income == "N/A":
                            net_income = extract_financial_metric(
                                report, ["Net Income", "netIncome", "net_income"]
                            )
                    except Exception as e:
                        logger.warning(f"Failed to extract metrics from report: {e}")

            # Get quarter/year information
            year = report_data.get("year", "")
            quarter = report_data.get("quarter", "")
            if year and quarter:
                report_period = f"Q{quarter} {year}"
            elif year:
                report_period = f"{year}"

        # Process earnings
        eps = date = "N/A"
        quarter_info = ""
        if earnings and isinstance(earnings, list) and len(earnings) > 0:
            try:
                # Sort earnings by date, newest first
                sorted_earnings = sorted(
                    earnings,
                    key=lambda x: datetime.strptime(
                        x.get("period", "1900-01-01"), "%Y-%m-%d"
                    ),
                    reverse=True,
                )
                latest = sorted_earnings[0]

                # Get EPS data from eps_actual if available (new format) or fallback to older attributes
                eps = (
                    latest.get("actual")
                    or latest.get("eps_actual")
                    or latest.get("epsActual")
                    or "N/A"
                )
                date = latest.get("period", "N/A")

                # Add quarter information
                if date != "N/A":
                    date_obj = datetime.strptime(date, "%Y-%m-%d")
                    month = date_obj.month
                    year = date_obj.year
                    quarter = (month - 1) // 3 + 1
                    quarter_info = f"Q{quarter} {year}"
            except Exception as e:
                logger.warning(
                    f"Could not parse earnings date for {symbol}", exc_info=True
                )

        # Determine visual classes for negative values
        net_income_class = ""
        eps_class = ""

        try:
            if isinstance(net_income, (int, float)) or (
                isinstance(net_income, str)
                and net_income.replace("-", "").replace(".", "").isdigit()
            ):
                net_income_value = float(str(net_income).replace(",", ""))
                if net_income_value < 0:
                    net_income_class = "text-danger"
        except (ValueError, TypeError):
            pass

        try:
            if isinstance(eps, (int, float)) or (
                isinstance(eps, str) and eps.replace("-", "").replace(".", "").isdigit()
            ):
                eps_value = float(str(eps).replace(",", ""))
                if eps_value < 0:
                    eps_class = "text-danger"
        except (ValueError, TypeError):
            pass

        # Get last update timestamp for data freshness indicator
        last_updated = datetime.now().strftime("%b %d, %Y %H:%M")

        # Format the financials section with Bootstrap styling
        return f"""
            <div class="row">
                <div class="col-6">
                    <div class="card bg-light mb-3">
                        <div class="card-body py-2">
                            <h6 class="card-title mb-1">Revenue</h6>
                            <p class="card-text fs-5">{format_financial_value(revenue) if revenue != "N/A" else '<span class="text-muted fst-italic">N/A</span>'}</p>
                            <small class="text-muted">{report_period}</small>
                        </div>
                    </div>
                </div>
                <div class="col-6">
                    <div class="card bg-light mb-3">
                        <div class="card-body py-2">
                            <h6 class="card-title mb-1">Net Income</h6>
                            <p class="card-text fs-5 {net_income_class}">{format_financial_value(net_income) if net_income != "N/A" else '<span class="text-muted fst-italic">N/A</span>'}</p>
                            <small class="text-muted">{report_period}</small>
                        </div>
                    </div>
                </div>
                <div class="col-6">
                    <div class="card bg-light mb-3">
                        <div class="card-body py-2">
                            <h6 class="card-title mb-1">EPS</h6>
                            <p class="card-text fs-5 {eps_class}">{format_financial_value(eps) if eps != "N/A" else '<span class="text-muted fst-italic">N/A</span>'}</p>
                            <small class="text-muted">{quarter_info}</small>
                        </div>
                    </div>
                </div>
                <div class="col-6">
                    <div class="card bg-light mb-3">
                        <div class="card-body py-2">
                            <h6 class="card-title mb-1">Earnings Date</h6>
                            <p class="card-text fs-5">{date if date != "N/A" else '<span class="text-muted fst-italic">N/A</span>'}</p>
                            <small class="text-muted">Last report</small>
                        </div>
                    </div>
                </div>
            </div>
            <div class="text-end mb-3">
                <small class="text-muted">Data as of: {last_updated}</small>
            </div>
        """

    # Process each stock in parallel
    threads = []
    for symbol in cannabis_stocks:
        t = threading.Thread(target=process_stock, args=(symbol,))
        threads.append(t)
        t.start()

    # Wait for all threads to complete
    for t in threads:
        t.join()

    # Update layout after all data is processed
    fig.update_layout(
        title=None,
        height=600,
        margin=dict(l=20, r=20, t=30, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
        xaxis=dict(rangeslider=dict(visible=False), type="date"),
        xaxis2=dict(type="date", rangeslider=dict(visible=True)),
        yaxis=dict(title="Price ($)", tickprefix="$", gridcolor="rgba(0,0,0,0.05)"),
        yaxis2=dict(title="Volume", gridcolor="rgba(0,0,0,0.05)"),
        plot_bgcolor="white",
        paper_bgcolor="white",
    )

    # Add range selector buttons
    fig.update_xaxes(
        rangeselector=dict(
            buttons=list(
                [
                    dict(count=1, label="1m", step="month", stepmode="backward"),
                    dict(count=3, label="3m", step="month", stepmode="backward"),
                    dict(count=6, label="6m", step="month", stepmode="backward"),
                    dict(count=1, label="YTD", step="year", stepmode="todate"),
                    dict(count=1, label="1y", step="year", stepmode="backward"),
                    dict(step="all"),
                ]
            ),
            bgcolor="white",
            activecolor="#0d6efd",
        ),
        row=1,
        col=1,
    )

    # Create timeframe tabs HTML for template
    timeframe_tabs = f"""
    <div class="card mb-4">
        <div class="card-body p-2">
            <div class="btn-group w-100" role="group">
                <a href="?timeframe=1m" class="btn btn-outline-primary {" active" if timeframe == "1m" else ""}">1 Month</a>
                <a href="?timeframe=3m" class="btn btn-outline-primary {" active" if timeframe == "3m" else ""}">3 Months</a>
                <a href="?timeframe=6m" class="btn btn-outline-primary {" active" if timeframe == "6m" or not timeframe else ""}">6 Months</a>
                <a href="?timeframe=1y" class="btn btn-outline-primary {" active" if timeframe == "1y" else ""}">1 Year</a>
                <a href="?timeframe=all" class="btn btn-outline-primary {" active" if timeframe == "all" else ""}">All Data</a>
            </div>
        </div>
    </div>
    """

    return render_template(
        "dashboard.html",
        graph=pio.to_html(fig, full_html=False, config={"responsive": True}),
        financials=financials_sections,
        news_sections=news_sections,
        timeframe_tabs=timeframe_tabs,
    )


def extract_financial_metric(report_data, possible_keys):
    """
    Helper to extract a metric from the income statement block.
    Tries to match one of the keys to the 'concept' field.
    """
    items = report_data.get("ic", [])  # 'ic' = Income Statement
    for item in items:
        concept = item.get("concept", "").lower()
        for key in possible_keys:
            if key.lower() in concept:
                return item.get("value", "N/A")
    return "N/A"


def extract_financial_metric_deep(report_data, possible_keys):
    """
    Deeper search helper to extract a metric from possibly nested structures.
    Will recursively look through various potential locations for financial data.
    """
    # First try extracting from standard format
    if isinstance(report_data, dict):
        # Try the standard income statement format
        if "ic" in report_data:
            result = extract_financial_metric(report_data, possible_keys)
            if result != "N/A":
                return result

        # Try the report.ic path (one level deeper)
        if "report" in report_data and isinstance(report_data["report"], dict):
            if "ic" in report_data["report"]:
                result = extract_financial_metric(report_data["report"], possible_keys)
                if result != "N/A":
                    return result

        # Try direct key access - sometimes financial metrics are directly in the root
        for key in possible_keys:
            if key.lower() in report_data:
                value = report_data.get(key.lower())
                if value is not None:
                    return value

    # Last resort: try to find any field that contains any of the keys at any level
    if isinstance(report_data, dict):
        for k, v in report_data.items():
            k_lower = k.lower()
            # Check if this key matches any of our target keys
            for target_key in possible_keys:
                if target_key.lower() in k_lower:
                    if isinstance(v, (int, float, str)):
                        return v
                    elif isinstance(v, dict) and "value" in v:
                        return v["value"]

            # Recursively search nested dictionaries
            if isinstance(v, dict):
                result = extract_financial_metric_deep(v, possible_keys)
                if result != "N/A":
                    return result
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        for ik, iv in item.items():
                            if any(key.lower() in ik.lower() for key in possible_keys):
                                return iv

                        # Check if this item has a concept that matches our keys
                        if "concept" in item:
                            concept = item["concept"].lower()
                            for key in possible_keys:
                                if key.lower() in concept:
                                    return item.get("value", "N/A")

    return "N/A"


def format_financial_value(value):
    """Format financial values for display"""
    if isinstance(value, (int, float)):
        # Determine if the value is negative
        is_negative = value < 0
        abs_value = abs(value)

        # Format based on magnitude
        if abs_value >= 1_000_000_000:
            formatted = f"${abs_value / 1_000_000_000:.2f}B"
        elif abs_value >= 1_000_000:
            formatted = f"${abs_value / 1_000_000:.2f}M"
        else:
            formatted = f"${abs_value:,.2f}"

        # Add negative sign if needed
        if is_negative:
            return "-" + formatted
        return formatted

    # Handle string values which may already be formatted
    elif isinstance(value, str):
        try:
            # Try to convert to float and reformat
            numeric_value = float(value.replace("$", "").replace(",", ""))
            return format_financial_value(numeric_value)
        except (ValueError, TypeError):
            # If it's not convertible to a number, return as is
            return value

    return value


@dashboard_bp.route("/download/<symbol>")
def download_csv(symbol):
    """
    Route to download stock data as CSV.
    By default, provides transformed data from database.
    If data_type=raw is specified, provides raw data directly from the API.
    """
    from flask import request

    data_type = request.args.get("data_type", "transformed")

    if data_type == "raw":
        # Get raw data directly from API
        try:
            raw_data = fetch_stock_data(symbol)
            if not raw_data or "Time Series (Daily)" not in raw_data:
                return Response("No data available for this symbol", status=404)

            time_series = raw_data["Time Series (Daily)"]

            # Prepare CSV file in memory
            output = io.StringIO()
            writer = csv.writer(output)

            # Write header
            writer.writerow(["date", "open", "high", "low", "close", "volume"])

            # Write data
            for date, values in time_series.items():
                writer.writerow(
                    [
                        date,
                        values["1. open"],
                        values["2. high"],
                        values["3. low"],
                        values["4. close"],
                        values["5. volume"],
                    ]
                )

            # Prepare response
            output.seek(0)
            filename = f"{symbol}_raw_data_{datetime.now().strftime('%Y%m%d')}.csv"

        except Exception as e:
            logger.error(f"Error fetching raw data for {symbol}: {e}", exc_info=True)
            return Response(f"Error fetching data: {str(e)}", status=500)
    else:
        # Get transformed data from database
        try:
            session = SessionLocal()
            query = (
                session.query(StockPrice)
                .filter(StockPrice.symbol == symbol)
                .order_by(StockPrice.date.asc())
            )
            records = [r.__dict__ for r in query]
            for r in records:
                r.pop("_sa_instance_state", None)
            session.close()

            if not records:
                return Response("No data available for this symbol", status=404)

            # Convert to pandas DataFrame
            df = pd.DataFrame(records)

            # Create CSV in memory
            output = io.StringIO()
            df.to_csv(output, index=False)

            # Prepare response
            output.seek(0)
            filename = (
                f"{symbol}_transformed_data_{datetime.now().strftime('%Y%m%d')}.csv"
            )

        except Exception as e:
            logger.error(
                f"Error fetching transformed data for {symbol}: {e}", exc_info=True
            )
            return Response(f"Error fetching data: {str(e)}", status=500)

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"},
    )


@dashboard_bp.route("/cache-control", methods=["GET", "POST"])
def cache_control():
    """Admin endpoint to view and clear cache."""
    from flask import redirect, url_for, flash, request

    if request.method == "POST" and request.form.get("action") == "clear_cache":
        clear_cache()
        return redirect(url_for("dashboard.cache_control"))

    stats = get_cache_stats()

    # Create a simple HTML page to display cache info
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Cache Control</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
        <div class="container mt-5">
            <h2 class="mb-4">Cache Control Panel</h2>
            
            <div class="card mb-4">
                <div class="card-header">Cache Statistics</div>
                <div class="card-body">
                    <p><strong>Entries:</strong> {stats["entries"]}</p>
                    <p><strong>Estimated Size:</strong> {stats["size_estimate"]} bytes</p>
                    <p><strong>Oldest Entry:</strong> {datetime.fromtimestamp(stats["oldest_entry"]).strftime("%Y-%m-%d %H:%M:%S") if stats["oldest_entry"] else "N/A"}</p>
                    <p><strong>Newest Entry:</strong> {datetime.fromtimestamp(stats["newest_entry"]).strftime("%Y-%m-%d %H:%M:%S") if stats["newest_entry"] else "N/A"}</p>
                </div>
            </div>
            
            <form method="POST">
                <input type="hidden" name="action" value="clear_cache">
                <button type="submit" class="btn btn-danger">Clear Cache</button>
                <a href="{{ url_for('dashboard.dashboard') }}" class="btn btn-secondary ms-2">Back to Dashboard</a>
            </form>
        </div>
    </body>
    </html>
    """

    return html
