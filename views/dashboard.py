from flask import Blueprint, render_template, Response, request, g
import pandas as pd
import polars as pl
from plotly.subplots import make_subplots
import plotly.graph_objs as go
import plotly.io as pio
from datetime import datetime, timedelta
import io
import csv
from services.news import fetch_company_news
from services.financials import fetch_financials
from services.earnings import fetch_earnings
from models.db_models import SessionLocal, StockPrice
from utils.logging_config import logger
from etl.extraction import fetch_stock_data
from etl.transformation import transform_stock_data
import threading
from utils.cache import timed_cache, clear_cache, get_cache_stats
import numpy as np

dashboard_bp = Blueprint("dashboard", __name__)


# Define the background data loading mechanism
def load_stock_data_background():
    """Load all stock data in the background to warm up cache"""
    cannabis_stocks = ["CGC", "ACB", "CRON", "TLRY"]
    for symbol in cannabis_stocks:
        try:
            fetch_company_news(symbol)
            fetch_financials(symbol)
            fetch_earnings(symbol)
        except Exception as e:
            logger.error(f"Error preloading data for {symbol}: {e}")


# Start background data loading on module import
threading.Thread(target=load_stock_data_background, daemon=True).start()


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
    from flask import request

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

        # Get and process news (cached)
        news = fetch_company_news(symbol)
        news_html = process_news(news, symbol)

        # Get financials and earnings (cached)
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
        financials = fetch_financials(symbol, freq="quarterly")
        if not financials or not financials.get("data"):
            financials = fetch_financials(symbol, freq="annual")

        earnings = fetch_earnings(symbol)

        # Process financials
        if financials and financials.get("data"):
            report = financials["data"][0].get("report", {})
            revenue = extract_financial_metric(
                report, ["Revenue", "totalRevenue", "revenues"]
            )
            net_income = extract_financial_metric(
                report, ["Net Income", "netIncome", "net_income"]
            )
        else:
            revenue = net_income = "N/A"

        # Process earnings
        eps = date = "N/A"
        if earnings and isinstance(earnings, list):
            try:
                sorted_earnings = sorted(
                    earnings,
                    key=lambda x: datetime.strptime(
                        x.get("period", "1900-01-01"), "%Y-%m-%d"
                    ),
                    reverse=True,
                )
                latest = sorted_earnings[0]
                eps = (
                    latest.get("actual")
                    or latest.get("eps")
                    or latest.get("epsActual")
                    or "N/A"
                )
                date = latest.get("period", "N/A")
            except Exception as e:
                logger.warning(
                    f"Could not parse earnings date for {symbol}", exc_info=True
                )

        # Format the financials section with Bootstrap styling
        return f"""
            <div class="row">
                <div class="col-6">
                    <div class="card bg-light mb-3">
                        <div class="card-body py-2">
                            <h6 class="card-title mb-1">Revenue</h6>
                            <p class="card-text fs-5">{revenue}</p>
                        </div>
                    </div>
                </div>
                <div class="col-6">
                    <div class="card bg-light mb-3">
                        <div class="card-body py-2">
                            <h6 class="card-title mb-1">Net Income</h6>
                            <p class="card-text fs-5">{net_income}</p>
                        </div>
                    </div>
                </div>
                <div class="col-6">
                    <div class="card bg-light mb-3">
                        <div class="card-body py-2">
                            <h6 class="card-title mb-1">EPS</h6>
                            <p class="card-text fs-5">{eps}</p>
                        </div>
                    </div>
                </div>
                <div class="col-6">
                    <div class="card bg-light mb-3">
                        <div class="card-body py-2">
                            <h6 class="card-title mb-1">Earnings Date</h6>
                            <p class="card-text fs-5">{date}</p>
                        </div>
                    </div>
                </div>
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
