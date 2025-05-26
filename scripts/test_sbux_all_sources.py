#!/usr/bin/env python3
"""
Test script to verify our multi-layer data source approach works for SBUX.
This will walk through each layer in our data fetch strategy:
1. Database
2. ETL (which triggers Finnhub API)
3. Yahoo Finance
4. Hardcoded data
"""

import json
import os
import sys
from datetime import datetime

# Add parent directory to path so we can import from the application modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import desc

from models.db_models import Earnings, FinancialReport, SessionLocal, create_tables
from services.alternative_financials import fetch_yahoo_financials
from services.earnings import fetch_earnings
from services.financials import fetch_financials
from services.hardcoded_financials import (
    get_hardcoded_earnings,
    get_hardcoded_financials,
)
from utils.logging_config import logger


def test_sbux_data_sources():
    """Test the complete multi-layer data source strategy for SBUX."""
    print("\n=== Testing Multi-Source Strategy for SBUX ===\n")

    # Ensure tables exist
    create_tables()

    # Step 1: Test hardcoded data first to ensure it works
    print("1. Hardcoded Data Source:")
    print("\n   Hardcoded Financials:")
    hardcoded_financials = get_hardcoded_financials("SBUX", "quarterly")
    if hardcoded_financials and hardcoded_financials.get("data"):
        print(
            f"   ✅ Found {len(hardcoded_financials['data'])} hardcoded quarterly financial reports"
        )
        print(f"   Source: {hardcoded_financials.get('source')}")

        if hardcoded_financials["data"]:
            latest = hardcoded_financials["data"][0]
            print(f"   Latest period: Q{latest.get('quarter')} {latest.get('year')}")

            # Extract and display revenue and net income
            revenue = None
            net_income = None
            for item in latest.get("report", {}).get("ic", []):
                if "revenue" in item.get("concept", "").lower():
                    revenue = item.get("value")
                if "net income" in item.get("concept", "").lower():
                    net_income = item.get("value")

            print(f"   Revenue: ${revenue / 1000000:.2f}M")
            print(f"   Net Income: ${net_income / 1000000:.2f}M")
    else:
        print("   ❌ No hardcoded financials found")

    print("\n   Hardcoded Earnings:")
    hardcoded_earnings = get_hardcoded_earnings("SBUX")
    if hardcoded_earnings:
        print(f"   ✅ Found {len(hardcoded_earnings)} hardcoded earnings reports")
        if hardcoded_earnings:
            latest = hardcoded_earnings[0]
            print(f"   Latest period: {latest.get('period')}")
            print(f"   EPS: {latest.get('actual')}")
            print(f"   Source: {latest.get('source')}")
    else:
        print("   ❌ No hardcoded earnings found")

    # Step 2: Test complete service flow to verify the fallback works
    print("\n2. Complete Service Flow:")
    print("\n   Financials Service:")
    financials = fetch_financials("SBUX", freq="quarterly")

    if financials and financials.get("data"):
        print(f"   ✅ Financials found via service adapter")
        print(f"   Source: {financials.get('source', 'unknown')}")
        print(f"   Reports: {len(financials['data'])}")

        if financials["data"]:
            latest = financials["data"][0]
            print(f"   Latest period: Q{latest.get('quarter')} {latest.get('year')}")

            # Extract revenue and net income if available
            try:
                revenue = None
                net_income = None

                if "report" in latest and "ic" in latest["report"]:
                    for item in latest["report"]["ic"]:
                        if "revenue" in item.get("concept", "").lower():
                            revenue = item.get("value")
                        if "net income" in item.get("concept", "").lower():
                            net_income = item.get("value")

                if revenue is not None:
                    print(f"   Revenue: ${revenue / 1000000:.2f}M")
                if net_income is not None:
                    print(f"   Net Income: ${net_income / 1000000:.2f}M")
            except Exception as e:
                print(f"   Error parsing financial data: {e}")
    else:
        print("   ❌ No financials found via service adapter")

    print("\n   Earnings Service:")
    earnings = fetch_earnings("SBUX")

    if earnings:
        print(f"   ✅ Earnings found via service adapter")
        if isinstance(earnings, list) and len(earnings) > 0:
            print(f"   Source: {earnings[0].get('source', 'unknown')}")
            print(f"   Reports: {len(earnings)}")
            print(f"   Latest EPS: {earnings[0].get('actual')}")
    else:
        print("   ❌ No earnings found via service adapter")

    # Print conclusion
    print("\n=== Test Summary ===")
    if financials and financials.get("data"):
        if financials.get("source") == "finnhub":
            print("✅ Financials sourced from: Finnhub API")
        elif financials.get("source") == "yahoo_finance":
            print("✅ Financials sourced from: Yahoo Finance (fallback)")
        elif financials.get("source") == "Starbucks Investor Relations":
            print("✅ Financials sourced from: Hardcoded data (last resort)")
        else:
            print(f"✅ Financials sourced from: {financials.get('source')}")

    if earnings and len(earnings) > 0:
        print(f"✅ Earnings sourced from: {earnings[0].get('source', 'unknown')}")


if __name__ == "__main__":
    try:
        test_sbux_data_sources()
    except Exception as e:
        print(f"Error running test: {e}")
        import traceback

        traceback.print_exc()
