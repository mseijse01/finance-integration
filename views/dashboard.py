from flask import Blueprint, render_template
import pandas as pd
import polars as pl
from plotly.subplots import make_subplots
import plotly.graph_objs as go
import plotly.io as pio
from services.news import fetch_company_news
from services.financials import fetch_financials
from services.earnings import fetch_earnings
from models.db_models import SessionLocal, StockPrice
from utils.logging_config import logger

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

        financials = fetch_financials(symbol)
        earnings = fetch_earnings(symbol)
        if financials.get("data"):
            report = financials["data"][0].get("report", {})
            revenue = next(
                (
                    report.get(k)
                    for k in ["Revenue", "totalRevenue", "revenues"]
                    if k in report
                ),
                "N/A",
            )
            net_income = next(
                (
                    report.get(k)
                    for k in ["Net Income", "netIncome", "net_income"]
                    if k in report
                ),
                "N/A",
            )
        else:
            revenue = net_income = "N/A"

        if (
            earnings
            and isinstance(earnings, list)
            and len(earnings) > 0
            and isinstance(earnings[0], dict)
        ):
            eps = earnings[0].get("eps", "N/A")
            date = earnings[0].get("period", "N/A")
        else:
            eps = date = "N/A"

        financials_sections[symbol] = (
            f"<p><strong>Revenue:</strong> {revenue}</p><p><strong>Net Income:</strong> {net_income}</p><p><strong>EPS:</strong> {eps}</p><p><strong>Earnings Date:</strong> {date}</p>"
        )

    fig.update_layout(title="Cannabis Stocks", height=600)
    return render_template(
        "dashboard.html",
        graph=pio.to_html(fig, full_html=False),
        financials=financials_sections,
        news_sections=news_sections,
    )
