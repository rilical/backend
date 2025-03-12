#!/usr/bin/env python3
"""
Verification script for aggregator-ready MukuruProvider implementation.
This script tests live API calls and confirms the standardized response format.
"""

import json
import logging
import os
import sys
from datetime import datetime
from decimal import Decimal

# Add the project root to Python path
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
)

from apps.providers.mukuru.integration import MukuruProvider

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def format_currency(amount, currency):
    """Format currency amount with proper precision."""
    if currency in ["ZAR"]:
        return f"R{float(amount):.2f}"
    return f"{float(amount):.2f} {currency}"


def print_response(title, response):
    """Format and print response data in a readable format."""
    print(f"\n{'-' * 80}")
    print(f"{title}")
    print(f"{'-' * 80}")

    if not response.get("success", False):
        print(f"❌ Error: {response.get('error_message', 'Unknown error')}")
        return

    # Print primary information
    print(f"✅ Success: {response['success']}")

    # Print common fields
    if "send_amount" in response and "source_currency" in response:
        print(
            f"Send: {format_currency(response['send_amount'], response['source_currency'])}"
        )

    if "destination_amount" in response and "destination_currency" in response:
        print(
            f"Receive: {format_currency(response['destination_amount'], response['destination_currency'])}"
        )

    if "exchange_rate" in response:
        print(f"Exchange Rate: {response['exchange_rate']}")
        # Verify that both exchange_rate and rate are the same (for aggregator compatibility)
        if "rate" in response and response["rate"] != response["exchange_rate"]:
            print(
                f"⚠️  Warning: 'rate' ({response['rate']}) differs from 'exchange_rate' ({response['exchange_rate']})"
            )
        else:
            print(f"Rate Field Validation: OK ✓")

    if "fee" in response:
        print(
            f"Fee: {format_currency(response['fee'], response.get('source_currency', 'ZAR'))}"
        )

    # Currency field validation
    if "destination_currency" in response and "target_currency" in response:
        dest = response["destination_currency"]
        target = response["target_currency"]
        if dest.upper() != target.upper():
            print(
                f"⚠️  Warning: 'destination_currency' ({dest}) differs from 'target_currency' ({target})"
            )
        else:
            print(f"Currency Field Validation: OK ✓")

    # Print provider-specific information
    print(f"Provider: {response['provider_id']}")
    print(f"Timestamp: {response['timestamp']}")

    # Print all fields for debugging
    print("\nAll Response Fields:")
    for key, value in sorted(response.items()):
        if key != "raw_response":  # Skip raw response for brevity
            print(f"  {key}: {value}")


def test_quotes():
    """Test get_quote with the aggregator-ready implementation."""
    provider = MukuruProvider()

    # Test cases for different corridors
    test_cases = [
        {
            "title": "ZAR → USD (South Africa to Zimbabwe)",
            "params": {
                "amount": Decimal("500.00"),
                "source_currency": "ZAR",
                "target_country": "ZW",
            },
        },
        {
            "title": "ZAR → NGN (South Africa to Nigeria)",
            "params": {
                "amount": Decimal("1000.00"),
                "source_currency": "ZAR",
                "target_country": "NG",
            },
        },
    ]

    print("\n===========================================================")
    print("TESTING AGGREGATOR-READY GET_QUOTE METHOD")
    print("===========================================================")

    for case in test_cases:
        try:
            logger.info(f"Testing quote: {case['title']}")
            result = provider.get_quote(**case["params"])
            print_response(f"Quote: {case['title']}", result)
        except Exception as e:
            logger.error(f"Error in {case['title']}: {e}")
            print(f"\n❌ Error in {case['title']}: {e}")


def test_exchange_rates():
    """Test get_exchange_rate with the aggregator-ready implementation."""
    provider = MukuruProvider()

    # Test cases for different currency pairs
    test_cases = [
        {
            "title": "ZAR → USD Exchange Rate (South Africa to Zimbabwe)",
            "params": {
                "send_amount": Decimal("900.00"),
                "send_currency": "ZAR",
                "receive_country": "ZW",
            },
        },
        {
            "title": "ZAR → MWK Exchange Rate (South Africa to Malawi)",
            "params": {
                "send_amount": Decimal("700.00"),
                "send_currency": "ZAR",
                "receive_country": "MW",
            },
        },
    ]

    print("\n===========================================================")
    print("TESTING AGGREGATOR-READY GET_EXCHANGE_RATE METHOD")
    print("===========================================================")

    for case in test_cases:
        try:
            logger.info(f"Testing exchange rate: {case['title']}")
            result = provider.get_exchange_rate(**case["params"])
            print_response(f"Exchange Rate: {case['title']}", result)
        except Exception as e:
            logger.error(f"Error in {case['title']}: {e}")
            print(f"\n❌ Error in {case['title']}: {e}")


def test_supported_countries():
    """Test retrieving supported countries."""
    provider = MukuruProvider()

    print("\n===========================================================")
    print("TESTING GET_SUPPORTED_COUNTRIES METHOD")
    print("===========================================================")

    try:
        countries = provider.get_supported_countries()
        print(f"Retrieved {len(countries)} supported countries:")
        for country_code, currency_code in countries.items():
            print(f"  {country_code}: {currency_code}")
    except Exception as e:
        logger.error(f"Error getting supported countries: {e}")
        print(f"\n❌ Error getting supported countries: {e}")


def main():
    """Run all tests."""
    try:
        print("\n📊 MUKURU AGGREGATOR-READY VERIFICATION 📊")
        print("\nTesting with live API calls to verify standardized responses...")

        test_supported_countries()
        test_quotes()
        test_exchange_rates()

        print("\n✅ Verification complete!")

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"\n❌ Unexpected error: {e}")


if __name__ == "__main__":
    main()
