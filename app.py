import ssl

import click
from flask import Flask

from models.db_models import create_tables
from run_etl import run_pipeline_for_symbol, run_pipelines_parallel
from views.dashboard import dashboard_bp
from views.news import news_bp

# Fix SSL certificate issues for NLTK downloads and other libraries
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

app = Flask(__name__)
create_tables()

app.register_blueprint(dashboard_bp)
app.register_blueprint(news_bp)


# Add CLI commands for running ETL processes
@app.cli.command("run-etl")
@click.option(
    "--symbol",
    help="Specific stock symbol to process (e.g., SBUX). If not provided, all default symbols will be processed.",
)
def run_etl_command(symbol=None):
    """Run the ETL pipeline to update the database with latest financial data."""
    if symbol:
        click.echo(f"Running ETL pipeline for symbol: {symbol}")
        success = run_pipeline_for_symbol(symbol)
        if success:
            click.echo(f"ETL pipeline completed successfully for {symbol}")
        else:
            click.echo(f"ETL pipeline had errors for {symbol}. Check logs for details.")
    else:
        click.echo("Running ETL pipeline for all default symbols")
        symbols = ["SBUX", "KDP", "BROS", "FARM"]
        results = run_pipelines_parallel(symbols)

        # Report results
        successful = [sym for sym, success in results.items() if success]
        failed = [sym for sym, success in results.items() if not success]

        if successful:
            click.echo(f"ETL completed successfully for: {', '.join(successful)}")
        if failed:
            click.echo(f"ETL had errors for: {', '.join(failed)}")

        click.echo("ETL process completed")


if __name__ == "__main__":
    app.run(debug=True)
