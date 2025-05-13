from flask import Blueprint, render_template
from services.news import fetch_company_news

news_bp = Blueprint("news", __name__)


@news_bp.route("/news")
def news():
    stocks = ["CGC", "ACB", "CRON", "TLRY"]
    news_sections = {}
    for symbol in stocks:
        articles = fetch_company_news(symbol)
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
