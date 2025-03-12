#!/usr/bin/env python3
"""
Verification script for the aggregator-ready KoronaPayProvider implementation.
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

from apps.providers.koronapay.exceptions import KoronaPayError
from apps.providers.koronapay.integration import KoronaPayProvider

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def format_currency(amount, currency):
    """Format currency amount with proper precision."""
    if currency in ["IDR", "VND"]:
        return f"{int(amount):,} {currency}"
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
        print(f"Fee: {response['fee']}")

    # Currency field validation
    if "source_currency" in response and "send_currency" in response.get(
        "raw_data", {}
    ):
        source = response["source_currency"]
        send = response.get("raw_data", {}).get("send_currency", "")
        if source.upper() != send.upper():
            print(
                f"⚠️  Warning: 'source_currency' ({source}) differs from 'send_currency' ({send})"
            )

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
    provider = KoronaPayProvider()

    # Test cases for different corridors
    test_cases = [
        {
            "title": "EUR → TRY (Spain to Turkey)",
            "params": {
                "send_amount": 500.0,
                "send_currency": "EUR",
                "receive_currency": "TRY",
                "send_country": "ESP",
                "receive_country": "TUR",
                "payment_method": "debit_card",
                "receiving_method": "cash",
            },
        },
        {
            "title": "EUR → TRY (Germany to Turkey)",
            "params": {
                "send_amount": 300.0,
                "send_currency": "EUR",
                "receive_currency": "TRY",
                "send_country": "DEU",
                "receive_country": "TUR",
                "payment_method": "debit_card",
                "receiving_method": "cash",
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
    provider = KoronaPayProvider()

    # Test cases for different currency pairs
    test_cases = [
        {
            "title": "EUR → TRY Exchange Rate (Spain to Turkey)",
            "params": {
                "send_currency": "EUR",
                "receive_currency": "TRY",
                "send_country": "ESP",
                "receive_country": "TUR",
                "amount": Decimal("100.00"),
            },
        },
        {
            "title": "EUR → TRY Exchange Rate (Germany to Turkey)",
            "params": {
                "send_currency": "EUR",
                "receive_currency": "TRY",
                "send_country": "DEU",
                "receive_country": "TUR",
                "amount": Decimal("200.00"),
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


def main():
    """Run all tests."""
    try:
        print("\n📊 KORONAPAY AGGREGATOR-READY VERIFICATION 📊")
        print("\nTesting with live API calls to verify standardized responses...")

        test_quotes()
        test_exchange_rates()

        print("\n✅ Verification complete!")

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"\n❌ Unexpected error: {e}")


if __name__ == "__main__":
    main()
