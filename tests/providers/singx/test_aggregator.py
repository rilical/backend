#!/usr/bin/env python3
"""
Test script for the aggregator-ready SingX provider implementation.
This script tests the SingX provider with live APIs to verify it works correctly.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from decimal import Decimal

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Add the parent directory to the path so we can import the provider
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../.."))
sys.path.insert(0, project_root)

# Import the provider
from apps.providers.singx.integration import SingXProvider
from apps.providers.singx.singx_mappings import (
    SUPPORTED_CORRIDORS,
    get_supported_destination_countries,
    get_supported_source_countries,
)


def format_json(data):
    """Format JSON data for pretty printing"""
    return json.dumps(data, indent=2, sort_keys=True)


def test_corridor(
    provider,
    amount,
    source_country,
    source_currency,
    destination_country,
    destination_currency,
    payment_method=None,
    delivery_method=None,
):
    """Test a specific corridor with the provider"""
    logger = logging.getLogger("test_corridor")

    logger.info(
        f"Testing corridor: {source_currency} ({source_country}) → "
        f"{destination_currency} ({destination_country}) for {amount} {source_currency}"
    )

    try:
        # Get a quote
        result = provider.get_quote(
            amount=Decimal(amount),
            source_currency=source_currency,
            destination_currency=destination_currency,
            source_country=source_country,
            destination_country=destination_country,
            payment_method=payment_method,
            delivery_method=delivery_method,
        )

        # Check if the request was successful
        if result["success"]:
            logger.info(
                f"✅ SUCCESS: {amount} {source_currency} → "
                f"{result['destination_amount']} {result['destination_currency']}"
            )
            logger.info(f"Exchange rate: {result['exchange_rate']}")
            logger.info(f"Fee: {result['fee']}")

            # Check if delivery methods are available
            if "available_delivery_methods" in result:
                logger.info(
                    f"Available delivery methods: {len(result['available_delivery_methods'])}"
                )
                for method in result["available_delivery_methods"]:
                    logger.info(
                        f"  - {method['method_name']} ({method['standardized_name']})"
                    )

            # Check if payment methods are available
            if "available_payment_methods" in result:
                logger.info(
                    f"Available payment methods: {len(result['available_payment_methods'])}"
                )
                for method in result["available_payment_methods"]:
                    logger.info(
                        f"  - {method['method_name']} ({method['standardized_name']})"
                    )

            return True
        else:
            logger.error(f"❌ FAILED: {result['error_message']}")
            return False

    except Exception as e:
        logger.error(f"❌ ERROR: {str(e)}", exc_info=True)
        return False


def test_with_receive_amount(
    provider,
    receive_amount,
    source_country,
    source_currency,
    destination_country,
    destination_currency,
):
    """Test a specific corridor with a receive amount instead of send amount"""
    logger = logging.getLogger("test_receive_amount")

    logger.info(
        f"Testing corridor with receive amount: {source_currency} ({source_country}) → "
        f"{receive_amount} {destination_currency} ({destination_country})"
    )

    try:
        # Get a quote
        result = provider.get_quote(
            receive_amount=Decimal(receive_amount),
            source_currency=source_currency,
            destination_currency=destination_currency,
            source_country=source_country,
            destination_country=destination_country,
        )

        # Check if the request was successful
        if result["success"]:
            logger.info(
                f"✅ SUCCESS: {result['send_amount']} {result['source_currency']} → "
                f"{receive_amount} {result['destination_currency']}"
            )
            logger.info(f"Exchange rate: {result['exchange_rate']}")
            logger.info(f"Fee: {result['fee']}")
            return True
        else:
            logger.error(f"❌ FAILED: {result['error_message']}")
            return False

    except Exception as e:
        logger.error(f"❌ ERROR: {str(e)}", exc_info=True)
        return False


def test_error_handling(provider):
    """Test that the provider properly handles errors and returns standardized error responses"""
    logger = logging.getLogger("test_error_handling")
    logger.info("Testing error handling")

    # Test an unsupported corridor
    try:
        result = provider.get_quote(
            amount=Decimal("1000"),
            source_currency="USD",  # Unsupported source currency for SG
            destination_currency="INR",
            source_country="SG",
            destination_country="IN",
        )

        if not result["success"] and result["error_message"]:
            logger.info(
                f"✅ Correctly handled unsupported corridor: {result['error_message']}"
            )
            return True
        else:
            logger.error("❌ Failed to handle unsupported corridor properly")
            return False
    except Exception as e:
        logger.error(
            f"❌ ERROR: Exception was raised instead of returning error response: {str(e)}"
        )
        return False


def main():
    """Main function to run the tests"""
    parser = argparse.ArgumentParser(
        description="Test the SingX provider implementation"
    )
    parser.add_argument("--amount", type=str, default="1000", help="Amount to send")
    parser.add_argument(
        "--source-country", type=str, default="SG", help="Source country code"
    )
    parser.add_argument(
        "--source-currency", type=str, default="SGD", help="Source currency"
    )
    parser.add_argument(
        "--destination-country", type=str, default="IN", help="Destination country code"
    )
    parser.add_argument(
        "--destination-currency", type=str, default="INR", help="Destination currency"
    )
    parser.add_argument(
        "--payment", type=str, help="Payment method (e.g., bank_transfer)"
    )
    parser.add_argument(
        "--delivery", type=str, help="Delivery method (e.g., bank_deposit)"
    )
    parser.add_argument(
        "--test-all", action="store_true", help="Test all supported corridors"
    )
    parser.add_argument(
        "--test-receive",
        action="store_true",
        help="Test with receive amount instead of send amount",
    )
    parser.add_argument(
        "--test-errors", action="store_true", help="Test error handling"
    )

    args = parser.parse_args()

    # Create the provider
    provider = SingXProvider()

    try:
        if args.test_errors:
            # Test error handling
            print("\n=== Testing error handling ===\n")
            test_error_handling(provider)

        elif args.test_receive:
            # Test with receive amount
            print(
                f"\n=== Testing {args.source_currency} ({args.source_country}) → "
                f"{args.amount} {args.destination_currency} ({args.destination_country}) ===\n"
            )
            test_with_receive_amount(
                provider,
                args.amount,
                args.source_country,
                args.source_currency,
                args.destination_country,
                args.destination_currency,
            )

        elif args.test_all:
            # Test all supported corridors
            print("\n=== Testing all supported corridors ===\n")

            # Define test corridors based on supported corridors
            test_corridors = []
            for (
                source_country,
                source_currency,
                dest_country,
                dest_currency,
            ) in SUPPORTED_CORRIDORS:
                test_corridors.append(
                    {
                        "source_country": source_country,
                        "source_currency": source_currency,
                        "destination_country": dest_country,
                        "destination_currency": dest_currency,
                        "amount": "1000",
                    }
                )

            success_count = 0
            for corridor in test_corridors:
                print(
                    f"\n--- Testing {corridor['source_currency']} ({corridor['source_country']}) → "
                    f"{corridor['destination_currency']} ({corridor['destination_country']}) ---"
                )
                if test_corridor(
                    provider,
                    corridor["amount"],
                    corridor["source_country"],
                    corridor["source_currency"],
                    corridor["destination_country"],
                    corridor["destination_currency"],
                ):
                    success_count += 1

            print(
                f"\n=== Test Results: {success_count}/{len(test_corridors)} corridors successful ==="
            )

        else:
            # Test a single corridor
            print(
                f"\n=== Testing {args.source_currency} ({args.source_country}) → "
                f"{args.destination_currency} ({args.destination_country}) for {args.amount} {args.source_currency} ===\n"
            )
            test_corridor(
                provider,
                args.amount,
                args.source_country,
                args.source_currency,
                args.destination_country,
                args.destination_currency,
                args.payment,
                args.delivery,
            )

    finally:
        # Close the provider session
        provider.close()


if __name__ == "__main__":
    main()
