#!/usr/bin/env python3
"""
Test script for the Western Union aggregator integration.

This script tests the updated WesternUnionProvider to verify it works
correctly with the aggregator pattern, returning standardized responses.

Usage:
    python test_aggregator_integration.py [--debug]
"""

import argparse
import json
import logging
import os
import pprint
import sys
import time
from decimal import Decimal
from typing import Any, Dict

# Add parent directory to path so we can import correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

# Import the provider
from providers.westernunion.integration import WesternUnionProvider

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("westernunion_test")

# List of test corridors to try
TEST_CORRIDORS = [
    # Common corridors
    {
        "source_country": "US",
        "source_currency": "USD",
        "destination_country": "MX",
        "destination_currency": "MXN",
        "amount": "1000",
    },
    {
        "source_country": "US",
        "source_currency": "USD",
        "destination_country": "CO",
        "destination_currency": "COP",
        "amount": "1000",
    },
    {
        "source_country": "US",
        "source_currency": "USD",
        "destination_country": "JM",
        "destination_currency": "JMD",
        "amount": "1000",
    },
    # European corridors
    {
        "source_country": "DE",
        "source_currency": "EUR",
        "destination_country": "TR",
        "destination_currency": "TRY",
        "amount": "1000",
    },
    {
        "source_country": "GB",
        "source_currency": "GBP",
        "destination_country": "PH",
        "destination_currency": "PHP",
        "amount": "1000",
    },
    # Less common corridors
    {
        "source_country": "NO",
        "source_currency": "NOK",
        "destination_country": "BN",
        "destination_currency": "BND",
        "amount": "1000",
    },
    {
        "source_country": "PL",
        "source_currency": "PLN",
        "destination_country": "LT",
        "destination_currency": "EUR",
        "amount": "1000",
    },
    # Expected failure case
    {
        "source_country": "ZZ",
        "source_currency": "USD",
        "destination_country": "ZZ",
        "destination_currency": "ZZZ",
        "amount": "1000",
    },
]


def pretty_print_result(result: Dict[str, Any], title: str = None) -> None:
    """Format and print a result dictionary."""
    if title:
        print(f"\n{'-' * 40}\n{title}\n{'-' * 40}")

    # Extract key information for summary
    success = result.get("success", False)
    provider = result.get("provider_id", "Unknown")
    error = result.get("error_message")

    # Print summary line
    if success:
        source_amount = result.get("send_amount", 0)
        source_currency = result.get("source_currency", "")
        dest_amount = result.get("destination_amount", 0)
        dest_currency = result.get("destination_currency", "")
        rate = result.get("exchange_rate", 0)
        fee = result.get("fee", 0)

        print(
            f"✅ SUCCESS: {provider} - {source_amount} {source_currency} → {dest_amount} {dest_currency}"
        )
        print(
            f"   Rate: {rate}  |  Fee: {fee}  |  Delivery method: {result.get('delivery_method', 'Unknown')}"
        )
    else:
        print(f"❌ FAILED: {provider} - Error: {error}")

    # Print full details if requested
    if logger.level <= logging.DEBUG:
        print("\nFull Response:")
        # Remove raw_response from printed output for clarity
        if "raw_response" in result:
            result_clean = {k: v for k, v in result.items() if k != "raw_response"}
            pprint.pprint(result_clean)
        else:
            pprint.pprint(result)


def test_corridor(provider: WesternUnionProvider, params: Dict[str, Any]) -> Dict[str, Any]:
    """Test a single corridor with parameters."""
    source_country = params.get("source_country")
    dest_country = params.get("destination_country")

    print(f"\nTesting corridor: {source_country} → {dest_country}")
    print(f"Parameters: {params}")

    try:
        amount = Decimal(params.get("amount", "1000"))
        result = provider.get_quote(
            amount=amount,
            source_currency=params.get("source_currency"),
            destination_currency=params.get("destination_currency"),
            source_country=source_country,
            destination_country=dest_country,
        )

        pretty_print_result(result)
        return result
    except Exception as e:
        logger.error(f"Exception during get_quote: {e}", exc_info=True)
        return {
            "provider_id": "Western Union",
            "success": False,
            "error_message": f"Test exception: {str(e)}",
        }


def main():
    parser = argparse.ArgumentParser(description="Test Western Union aggregator integration")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--corridor", type=int, help="Test a specific corridor by index (0-7)")
    parser.add_argument("--sleep", type=int, default=2, help="Sleep time between tests (seconds)")
    args = parser.parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)
        logging.getLogger("westernunion").setLevel(logging.DEBUG)

    print(f"\n{'=' * 80}")
    print(f"WESTERN UNION AGGREGATOR INTEGRATION TEST")
    print(f"{'=' * 80}")

    # Create provider instance
    provider = WesternUnionProvider(timeout=60)

    # Test all corridors or specific one
    success_count = 0
    fail_count = 0

    if args.corridor is not None and 0 <= args.corridor < len(TEST_CORRIDORS):
        # Test specific corridor
        result = test_corridor(provider, TEST_CORRIDORS[args.corridor])
        if result.get("success"):
            success_count += 1
        else:
            fail_count += 1
    else:
        # Test all corridors
        for i, corridor in enumerate(TEST_CORRIDORS):
            print(f"\nTest #{i+1} of {len(TEST_CORRIDORS)}")
            result = test_corridor(provider, corridor)

            if result.get("success"):
                success_count += 1
            else:
                fail_count += 1

            # Sleep between tests to avoid rate limiting
            if i < len(TEST_CORRIDORS) - 1:
                print(f"Sleeping for {args.sleep} seconds...")
                time.sleep(args.sleep)

    # Display summary
    print(f"\n{'=' * 80}")
    print(f"TEST SUMMARY")
    print(f"{'=' * 80}")
    print(f"Total corridors tested: {success_count + fail_count}")
    print(f"Successful quotes: {success_count}")
    print(f"Failed quotes: {fail_count}")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    main()
