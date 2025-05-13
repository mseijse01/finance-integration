from flask import Flask
from views.dashboard import dashboard_bp
from views.news import news_bp
from models.db_models import create_tables

app = Flask(__name__)
create_tables()

app.register_blueprint(dashboard_bp)
app.register_blueprint(news_bp)

if __name__ == "__main__":
    app.run(debug=True)
