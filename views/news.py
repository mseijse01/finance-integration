from flask import Blueprint, render_template

from services.news import NewsService

news_bp = Blueprint("news", __name__)


@news_bp.route("/news")
def news():
    """News page showing sentiment analysis for all stocks"""
    # Define stocks to analyze
    stocks = ["SBUX", "KDP", "BROS", "FARM"]
    news_sections = {}
    for symbol in stocks:
        articles = NewsService.fetch_news(symbol)
        html = (
            "<ul>"
            + "".join(
                [
                    f"<li>{a['headline']} (<a href='{a['url']}' target='_blank'>link</a>)</li>"
                    for a in articles[:10]
                ]
            )
            + "</ul>"
        )
        news_sections[symbol] = html or "No recent news."
    return render_template("news.html", news_sections=news_sections)
