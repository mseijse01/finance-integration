from datetime import datetime

import requests

from config import Config
from models.db_models import FinancialReport, SessionLocal
from utils.logging_config import logger


def extract_financials(symbol: str, freq: str = "quarterly"):
    """
    Extract financial reports for a given stock symbol from Finnhub.
    """
    url = "https://finnhub.io/api/v1/stock/financials-reported"
    params = {
        "symbol": symbol,
        "token": Config.FINNHUB_API_KEY,
        "freq": freq,
    }

    try:
        logger.info(f"[Financials ETL] Extracting {freq} financials for {symbol}")
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
            logger.info(
                f"[Financials ETL] Extracted {len(data['data'])} {freq} financial records for {symbol}"
            )
            return data
        elif isinstance(data, list):  # fallback case
            logger.warning(
                f"[Financials ETL] Unexpected format: financials returned as list for {symbol}"
            )
            return {"data": data}
        else:
            logger.warning(
                f"[Financials ETL] Unexpected financials format for {symbol}: {type(data)}"
            )
            return {"data": []}

    except Exception as e:
        logger.error(
            f"[Financials ETL] Error extracting financials for {symbol}: {e}",
            exc_info=True,
        )
        return {"data": []}


def transform_financials(financial_data, symbol, report_type):
    """
    Transform financial data by extracting key metrics and normalizing structure.
    """
    try:
        reports = financial_data.get("data", [])
        logger.info(
            f"[Financials ETL] Transforming {len(reports)} {report_type} reports for {symbol}"
        )

        transformed_reports = []

        for report in reports:
            # Extract quarter and year information
            year = report.get("year")
            quarter = report.get("quarter") if report_type == "quarterly" else None

            # Extract key financial metrics from the report
            report_data = report.get("report", {})

            # Get income statement items
            income_statement = report_data.get("ic", [])

            # Extract key metrics
            revenue = extract_financial_metric(
                income_statement, ["Revenue", "totalRevenue", "revenues"]
            )
            net_income = extract_financial_metric(
                income_statement, ["Net Income", "netIncome", "net_income"]
            )
            eps = extract_financial_metric(
                income_statement, ["EPS", "earningsPerShare", "eps"]
            )

            # Create normalized report structure
            transformed_report = {
                "symbol": symbol,
                "year": year,
                "quarter": quarter,
                "report_type": report_type,
                "filing_date": datetime.strptime(
                    report.get("filed", "1970-01-01"), "%Y-%m-%d"
                )
                if report.get("filed")
                else None,
                "report_data": report,  # Store the complete report data
                "revenue": revenue if revenue != "N/A" else None,
                "net_income": net_income if net_income != "N/A" else None,
                "eps": eps if eps != "N/A" else None,
            }

            transformed_reports.append(transformed_report)

        logger.info(
            f"[Financials ETL] Transformed {len(transformed_reports)} reports for {symbol}"
        )
        return transformed_reports

    except Exception as e:
        logger.error(
            f"[Financials ETL] Error transforming financials for {symbol}: {e}",
            exc_info=True,
        )
        return []


def extract_financial_metric(items, possible_keys):
    """
    Helper to extract a metric from the income statement items.
    Tries to match one of the keys to the 'concept' field.
    """
    for item in items:
        concept = item.get("concept", "").lower()
        for key in possible_keys:
            if key.lower() in concept:
                value = item.get("value")
                if value is not None:
                    try:
                        return float(value)
                    except (ValueError, TypeError):
                        return value
                return value
    return "N/A"


def load_financials_to_db(transformed_reports):
    """
    Load transformed financial reports into the database.
    """
    session = SessionLocal()
    try:
        logger.info(
            f"[Financials ETL] Loading {len(transformed_reports)} reports to database"
        )

        # For each report, create or update the database record
        for report_data in transformed_reports:
            # Check if the report already exists
            existing = (
                session.query(FinancialReport)
                .filter_by(
                    symbol=report_data["symbol"],
                    year=report_data["year"],
                    quarter=report_data["quarter"],
                    report_type=report_data["report_type"],
                )
                .first()
            )

            if existing:
                # Update existing record
                for key, value in report_data.items():
                    setattr(existing, key, value)
            else:
                # Create new record
                report = FinancialReport(**report_data)
                session.add(report)

        session.commit()
        logger.info("[Financials ETL] Financial reports loaded successfully")
    except Exception as e:
        session.rollback()
        logger.error(
            f"[Financials ETL] Error loading financial reports: {e}", exc_info=True
        )
    finally:
        session.close()


def run_financials_etl_pipeline(symbol):
    """
    Run the full ETL pipeline for financial data, processing both quarterly and annual reports.
    """
    success = True

    # Process quarterly financials
    try:
        logger.info(
            f"[Financials ETL] Starting quarterly financials ETL pipeline for {symbol}"
        )
        raw_quarterly = extract_financials(symbol, freq="quarterly")
        if raw_quarterly and raw_quarterly.get("data"):
            transformed_quarterly = transform_financials(
                raw_quarterly, symbol, "quarterly"
            )
            if transformed_quarterly:
                load_financials_to_db(transformed_quarterly)
        logger.info(
            f"[Financials ETL] Quarterly financials ETL pipeline completed for {symbol}"
        )
    except Exception as e:
        logger.error(
            f"[Financials ETL] Quarterly financials ETL pipeline failed for {symbol}: {e}",
            exc_info=True,
        )
        success = False

    # Process annual financials
    try:
        logger.info(
            f"[Financials ETL] Starting annual financials ETL pipeline for {symbol}"
        )
        raw_annual = extract_financials(symbol, freq="annual")
        if raw_annual and raw_annual.get("data"):
            transformed_annual = transform_financials(raw_annual, symbol, "annual")
            if transformed_annual:
                load_financials_to_db(transformed_annual)
        logger.info(
            f"[Financials ETL] Annual financials ETL pipeline completed for {symbol}"
        )
    except Exception as e:
        logger.error(
            f"[Financials ETL] Annual financials ETL pipeline failed for {symbol}: {e}",
            exc_info=True,
        )
        success = False

    return success
