from flask import Blueprint, render_template, Response
import pandas as pd
import polars as pl
from plotly.subplots import make_subplots
import plotly.graph_objs as go
import plotly.io as pio
from datetime import datetime
import io
import csv
from services.news import fetch_company_news
from services.financials import fetch_financials
from services.earnings import fetch_earnings
from models.db_models import SessionLocal, StockPrice
from utils.logging_config import logger
from etl.extraction import fetch_stock_data
from etl.transformation import transform_stock_data

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def dashboard():
    cannabis_stocks = ["CGC", "ACB", "CRON", "TLRY"]
    fig = make_subplots(rows=1, cols=1)
    news_sections = {}
    financials_sections = {}

    for symbol in cannabis_stocks:
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

        if records:
            df = pl.DataFrame(records).sort("date").to_pandas()
            fig.add_trace(
                go.Scatter(x=df["date"], y=df["close"], mode="lines", name=symbol)
            )

        news = fetch_company_news(symbol)
        if news:
            news_html = "<ul>"
            sentiments = []
            for article in news[:5]:
                sentiment = article.get("sentiment", 0)
                sentiments.append(sentiment)
                sentiment_level = (
                    "🟢" if sentiment > 0.5 else "🟡" if sentiment > 0 else "🔴"
                )
                news_html += f"<li>{article['headline']} (<a href='{article['url']}' target='_blank'>link</a>) - Sentiment: {sentiment:.2f} {sentiment_level}</li>"
            news_html += "</ul>"
            news_sections[symbol] = {
                "headlines": news_html,
                "average_sentiment": sum(sentiments) / len(sentiments),
            }
        else:
            news_sections[symbol] = {
                "headlines": "No recent news.",
                "average_sentiment": None,
            }

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

        financials_sections[symbol] = (
            f"<p><strong>Revenue:</strong> {revenue}</p>"
            f"<p><strong>Net Income:</strong> {net_income}</p>"
            f"<p><strong>EPS:</strong> {eps}</p>"
            f"<p><strong>Earnings Date:</strong> {date}</p>"
        )

    fig.update_layout(title="Cannabis Stocks", height=600)
    return render_template(
        "dashboard.html",
        graph=pio.to_html(fig, full_html=False),
        financials=financials_sections,
        news_sections=news_sections,
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
