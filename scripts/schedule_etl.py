#!/usr/bin/env python3
"""
Simple ETL Scheduling System
Provides automated data refresh for the finance dashboard.

This script can be run as:
1. A standalone scheduler daemon
2. A one-time scheduled job via cron
3. Manual trigger for testing
"""

import sys
import os
import time
import argparse
from datetime import datetime, timedelta

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import schedule
from run_etl import run_pipeline_for_symbol
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Stock symbols to refresh
COFFEE_STOCKS = ["SBUX", "KDP", "BROS", "FARM"]


def run_daily_etl():
    """
    Run the daily ETL process for all coffee stocks.
    """
    try:
        logger.info("Starting scheduled ETL run...")
        start_time = datetime.now()

        # Run ETL for each symbol
        success_count = 0
        error_count = 0

        for symbol in COFFEE_STOCKS:
            try:
                logger.info(f"Running ETL for {symbol}...")
                result = run_pipeline_for_symbol(symbol)

                if result:
                    success_count += 1
                    logger.info(f"✓ {symbol} ETL completed successfully")
                else:
                    error_count += 1
                    logger.warning(f"⚠ {symbol} ETL completed with warnings")

            except Exception as e:
                error_count += 1
                logger.error(f"✗ {symbol} ETL failed: {e}")

        # Log summary
        end_time = datetime.now()
        duration = end_time - start_time

        logger.info("=" * 50)
        logger.info(f"ETL Run Summary:")
        logger.info(f"- Duration: {duration}")
        logger.info(f"- Successful: {success_count}/{len(COFFEE_STOCKS)}")
        logger.info(f"- Errors: {error_count}/{len(COFFEE_STOCKS)}")
        logger.info(f"- Next run: {schedule.next_run()}")
        logger.info("=" * 50)

        return success_count > 0  # Return True if at least one symbol succeeded

    except Exception as e:
        logger.error(f"Daily ETL run failed: {e}")
        return False


def run_scheduler_daemon():
    """
    Run the scheduler as a daemon process.
    """
    logger.info("Starting ETL Scheduler Daemon...")
    logger.info(f"Configured to refresh: {', '.join(COFFEE_STOCKS)}")

    # Schedule daily ETL at 6:00 AM (before market open)
    schedule.every().day.at("06:00").do(run_daily_etl)

    # Schedule a light refresh every 4 hours during market hours
    schedule.every(4).hours.do(run_daily_etl)

    logger.info("Scheduled jobs:")
    logger.info("- Daily full refresh: 6:00 AM")
    logger.info("- Light refresh: Every 4 hours")
    logger.info(f"Next scheduled run: {schedule.next_run()}")

    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

    except KeyboardInterrupt:
        logger.info("Scheduler daemon stopped by user")
    except Exception as e:
        logger.error(f"Scheduler daemon error: {e}")
        raise


def create_cron_job():
    """
    Create a cron job for automated ETL scheduling.
    """
    script_path = os.path.abspath(__file__)
    python_path = sys.executable

    # Cron job to run daily at 6:00 AM
    cron_command = f"0 6 * * * {python_path} {script_path} --run-once >> /tmp/etl_scheduler.log 2>&1"

    print("To set up automated ETL scheduling, add this cron job:")
    print("Run: crontab -e")
    print("Add this line:")
    print(cron_command)
    print()
    print(
        "This will run the ETL daily at 6:00 AM and log output to /tmp/etl_scheduler.log"
    )
    print()
    print("To view logs: tail -f /tmp/etl_scheduler.log")


def check_data_freshness():
    """
    Check the freshness of data in the database.
    """
    from models.db_models import get_db_session, StockPrice
    from sqlalchemy import func

    try:
        session = get_db_session()

        logger.info("Checking data freshness...")

        for symbol in COFFEE_STOCKS:
            # Get the latest data for this symbol
            latest_record = (
                session.query(StockPrice)
                .filter(StockPrice.symbol == symbol)
                .order_by(StockPrice.date.desc())
                .first()
            )

            if latest_record:
                days_old = (datetime.now().date() - latest_record.date).days
                freshness_status = (
                    "FRESH" if days_old <= 1 else "STALE" if days_old <= 7 else "OLD"
                )
                logger.info(
                    f"{symbol}: Latest data {latest_record.date} ({days_old} days old) - {freshness_status}"
                )
            else:
                logger.warning(f"{symbol}: No data found")

        session.close()

    except Exception as e:
        logger.error(f"Failed to check data freshness: {e}")


def main():
    """
    Main function with command line argument parsing.
    """
    global COFFEE_STOCKS
    parser = argparse.ArgumentParser(description="ETL Scheduling System")
    parser.add_argument(
        "--daemon", action="store_true", help="Run as daemon with continuous scheduling"
    )
    parser.add_argument(
        "--run-once", action="store_true", help="Run ETL once and exit (for cron jobs)"
    )
    parser.add_argument(
        "--create-cron", action="store_true", help="Show cron job setup instructions"
    )
    parser.add_argument(
        "--check-freshness", action="store_true", help="Check data freshness and exit"
    )
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=COFFEE_STOCKS,
        help="Symbols to process (default: all coffee stocks)",
    )

    args = parser.parse_args()

    # Update symbols if provided
    if args.symbols != COFFEE_STOCKS:
        COFFEE_STOCKS = args.symbols
        logger.info(f"Using custom symbols: {', '.join(COFFEE_STOCKS)}")

    try:
        if args.daemon:
            run_scheduler_daemon()

        elif args.run_once:
            logger.info("Running one-time ETL job...")
            success = run_daily_etl()
            sys.exit(0 if success else 1)

        elif args.create_cron:
            create_cron_job()

        elif args.check_freshness:
            check_data_freshness()

        else:
            # Default: show help and options
            print("ETL Scheduler - Choose an option:")
            print()
            print("1. Run as daemon (continuous scheduling):")
            print(f"   python {os.path.basename(__file__)} --daemon")
            print()
            print("2. Run once and exit (for cron):")
            print(f"   python {os.path.basename(__file__)} --run-once")
            print()
            print("3. Set up cron job:")
            print(f"   python {os.path.basename(__file__)} --create-cron")
            print()
            print("4. Check data freshness:")
            print(f"   python {os.path.basename(__file__)} --check-freshness")
            print()
            parser.print_help()

    except Exception as e:
        logger.error(f"Scheduler error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
