#!/usr/bin/env python3
"""
Test script to verify Yahoo Finance integration for SBUX.
Ensures that our alternative data sources work correctly.
"""

import json
import os
import sys

# Add parent directory to path so we can import from the application modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import services.earnings
import services.financials
from services.alternative_financials import fetch_yahoo_financials
from utils.logging_config import logger


def test_yahoo_finance_integration():
    """Test the complete Yahoo Finance integration for SBUX."""
    print("\n=== Testing Yahoo Finance Integration for SBUX ===\n")

    # Test direct Yahoo Finance API
    print("1. Direct Yahoo Finance API Call:")
    yahoo_data = fetch_yahoo_financials("SBUX")

    # Check quarterly financials
    print("\n   Quarterly Financials:")
    if yahoo_data["quarterly_financials"] and yahoo_data["quarterly_financials"].get(
        "data"
    ):
        quarterly = yahoo_data["quarterly_financials"]["data"]
        print(f"   ✅ Found {len(quarterly)} quarterly financial reports")
        if quarterly:
            latest = quarterly[0]
            print(f"   Latest period: Q{latest.get('quarter')} {latest.get('year')}")

            # Extract and display revenue and net income
            for item in latest.get("report", {}).get("ic", []):
                if "revenue" in item.get("concept", "").lower():
                    print(f"   Revenue: {item.get('value')}")
                if "net income" in item.get("concept", "").lower():
                    print(f"   Net Income: {item.get('value')}")
    else:
        print("   ❌ No quarterly financials found")

    # Check annual financials
    print("\n   Annual Financials:")
    if yahoo_data["annual_financials"] and yahoo_data["annual_financials"].get("data"):
        annual = yahoo_data["annual_financials"]["data"]
        print(f"   ✅ Found {len(annual)} annual financial reports")
        if annual:
            latest = annual[0]
            print(f"   Latest year: {latest.get('year')}")

            # Extract and display revenue and net income
            for item in latest.get("report", {}).get("ic", []):
                if "revenue" in item.get("concept", "").lower():
                    print(f"   Revenue: {item.get('value')}")
                if "net income" in item.get("concept", "").lower():
                    print(f"   Net Income: {item.get('value')}")
    else:
        print("   ❌ No annual financials found")

    # Check quarterly earnings
    print("\n   Quarterly Earnings:")
    if yahoo_data["quarterly_earnings"]:
        print(
            f"   ✅ Found {len(yahoo_data['quarterly_earnings'])} quarterly earnings reports"
        )
        if yahoo_data["quarterly_earnings"]:
            latest = yahoo_data["quarterly_earnings"][0]
            print(f"   Latest period: {latest.get('period')}")
            print(f"   EPS: {latest.get('actual')}")
    else:
        print("   ❌ No quarterly earnings found")

    # Test through service adapter
    print("\n2. Through Service Adapter:")
    print("\n   Financials Service:")
    financials = services.financials.fetch_financials("SBUX", freq="quarterly")

    if financials and financials.get("data"):
        print(f"   ✅ Financials found via service adapter")
        print(f"   Source: {financials.get('source', 'unknown')}")
        print(f"   Reports: {len(financials['data'])}")
    else:
        print("   ❌ No financials found via service adapter")

    print("\n   Earnings Service:")
    earnings = services.earnings.fetch_earnings("SBUX")

    if earnings:
        print(f"   ✅ Earnings found via service adapter")
        if isinstance(earnings, list) and len(earnings) > 0:
            print(f"   Source: {earnings[0].get('source', 'unknown')}")
            print(f"   Reports: {len(earnings)}")
    else:
        print("   ❌ No earnings found via service adapter")


if __name__ == "__main__":
    try:
        test_yahoo_finance_integration()
    except Exception as e:
        print(f"Error running test: {e}")
        import traceback

        traceback.print_exc()
