"""
Wise (TransferWise) Aggregator Tests

This module tests the Wise provider as an aggregator-ready integration,
verifying that it properly handles API calls and returns standardized responses.

The tests can be run with or without a valid API key:
- With API key: Tests make real API calls to Wise with authentication
- Without API key: Tests use the unauthenticated quote endpoint

Usage:
    python -m apps.providers.wise.test_aggregator --direct
    python -m apps.providers.wise.test_aggregator --live (requires WISE_API_KEY env var)
"""

import argparse
import json
import logging
import os
import sys
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

import requests

from apps.providers.wise.exceptions import WiseError
from apps.providers.wise.integration import WiseProvider

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("wise_test_aggregator")

# Sample exchange rate data for testing without API key
SAMPLE_EXCHANGE_DATA = {
    "sourceAmount": 100.0,
    "targetAmount": 91.58,
    "rate": 0.9158,
    "createdTime": "2025-03-07T12:34:56Z",
    "rateType": "FIXED",
    "status": "PENDING",
    "sourceCurrency": "USD",
    "targetCurrency": "EUR",
    "paymentOptions": [
        {
            "formattedEstimatedDelivery": "by Tomorrow",
            "estimatedDeliveryDelays": [],
            "allowedProfileTypes": ["PERSONAL", "BUSINESS"],
            "payInProduct": "CHEAP",
            "fee": {
                "transferwise": 4.13,
                "payIn": 0.0,
                "discount": 0.0,
                "partner": 0.0,
                "total": 4.13,
            },
            "sourceAmount": 100.0,
            "targetAmount": 91.58,
            "sourceCurrency": "USD",
            "targetCurrency": "EUR",
            "payIn": "BANK_TRANSFER",
            "payOut": "BANK_TRANSFER",
            "allowedShortCountryNames": [],
            "disallowedShortCountryNames": [],
            "disabled": False,
        },
        {
            "formattedEstimatedDelivery": "in 1-2 days",
            "estimatedDeliveryDelays": [],
            "allowedProfileTypes": ["PERSONAL", "BUSINESS"],
            "payInProduct": "CARD",
            "fee": {
                "transferwise": 4.13,
                "payIn": 2.36,
                "discount": 0.0,
                "partner": 0.0,
                "total": 6.49,
            },
            "sourceAmount": 100.0,
            "targetAmount": 89.43,
            "sourceCurrency": "USD",
            "targetCurrency": "EUR",
            "payIn": "CARD",
            "payOut": "BANK_TRANSFER",
            "allowedShortCountryNames": [],
            "disallowedShortCountryNames": [],
            "disabled": False,
        },
    ],
}

# Additional sample currency pairs
SAMPLE_CURRENCY_PAIRS = [
    {"source": "USD", "target": "MXN", "rate": 16.9047, "fee": 3.56},
    {"source": "EUR", "target": "GBP", "rate": 0.8521, "fee": 3.12},
    {"source": "GBP", "target": "INR", "rate": 105.43, "fee": 2.89},
    {"source": "CAD", "target": "USD", "rate": 0.7412, "fee": 2.44},
    {"source": "AUD", "target": "NZD", "rate": 1.1043, "fee": 4.02},
]


def get_exchange_rate_direct(
    source_currency: str, target_currency: str, amount: float = 100.0
) -> Dict[str, Any]:
    """
    Get exchange rate data directly using the unauthenticated quote endpoint.

    Args:
        source_currency: Source currency code
        target_currency: Target currency code
        amount: Amount to send

    Returns:
        Exchange rate data in aggregator-standard format
    """
    logger.info(f"Getting direct exchange rate for {source_currency} to {target_currency}")

    # Create a Wise provider instance
    wise = WiseProvider()

    # Get quote using the unauthenticated endpoint
    try:
        # Override the _create_quote method to use _create_unauthenticated_quote
        wise._create_quote = wise._create_unauthenticated_quote

        # Get the quote
        result = wise.get_quote(
            amount=Decimal(str(amount)),
            source_currency=source_currency,
            destination_currency=target_currency,
        )

        # Clean up
        wise.close()

        return result
    except Exception as e:
        logger.error(f"Error fetching from API: {str(e)}")

        # Clean up
        wise.close()

        # Return error response
        return {
            "provider_id": "wise",
            "success": False,
            "error_message": f"Error fetching exchange rate: {str(e)}",
        }


def run_tests(use_live_api: bool = False):
    """
    Run a series of tests to validate the Wise aggregator functionality.

    Args:
        use_live_api: Whether to use the live API with authentication (requires API key)
    """
    # Test various currency pairs
    test_cases = [
        {"source": "USD", "target": "EUR", "amount": 100},
        {"source": "USD", "target": "GBP", "amount": 200},
        {"source": "EUR", "target": "GBP", "amount": 50},
        {"source": "GBP", "target": "USD", "amount": 75},
        {"source": "USD", "target": "INR", "amount": 100},
    ]

    if not use_live_api:
        # When not using live API, use the unauthenticated endpoint
        logger.info("===== RUNNING TESTS WITH UNAUTHENTICATED API =====")
    else:
        # Check for API key when using live API with authentication
        if not os.environ.get("WISE_API_KEY"):
            logger.error("WISE_API_KEY environment variable is required for live API tests")
            sys.exit(1)
        logger.info("===== RUNNING TESTS WITH AUTHENTICATED API =====")

    # Run the tests
    for test in test_cases:
        source = test["source"]
        target = test["target"]
        amount = test["amount"]

        logger.info(f"\n===== Testing {source} -> {target} ({amount}) =====")

        try:
            if use_live_api:
                # Use WiseProvider directly with API key
                wise = WiseProvider(api_key=os.environ.get("WISE_API_KEY"))
                result = wise.get_quote(
                    amount=Decimal(str(amount)),
                    source_currency=source,
                    destination_currency=target,
                )
                wise.close()
            else:
                # Use direct function with unauthenticated endpoint
                result = get_exchange_rate_direct(source, target, amount)

            # Print the result
            if result["success"]:
                logger.info(f"✅ SUCCESS: {source} {amount} -> {target}")
                logger.info(f"  Exchange rate: {result['exchange_rate']}")
                logger.info(f"  Fee: {result['fee']}")
                logger.info(f"  Destination amount: {result['destination_amount']}")
                logger.info(f"  Delivery method: {result['delivery_method']}")
                logger.info(f"  Payment method: {result['payment_method']}")
                logger.info(f"  Delivery time (minutes): {result['delivery_time_minutes']}")
            else:
                logger.info(f"❌ FAILED: {source} {amount} -> {target}")
                logger.info(f"  Error: {result['error_message']}")

        except Exception as e:
            logger.error(f"Test error: {str(e)}")

    # Test error handling
    logger.info("\n===== Testing Error Handling =====")

    # Test invalid currency
    logger.info("\nTesting invalid currency:")
    result = get_exchange_rate_direct("USD", "XYZ", 100)

    if not result["success"]:
        logger.info(f"✅ SUCCESS: Properly handled invalid currency")
        logger.info(f"  Error: {result['error_message']}")
    else:
        logger.info(f"❌ FAILED: Did not properly handle invalid currency")

    # Test invalid amount
    logger.info("\nTesting invalid amount:")
    wise = WiseProvider()
    wise._create_quote = wise._create_unauthenticated_quote
    result = wise.get_quote(amount=Decimal("0"), source_currency="USD", destination_currency="EUR")
    wise.close()

    if not result["success"]:
        logger.info(f"✅ SUCCESS: Properly handled invalid amount")
        logger.info(f"  Error: {result['error_message']}")
    else:
        logger.info(f"❌ FAILED: Did not properly handle invalid amount")

    # Test missing amount
    logger.info("\nTesting missing amount:")
    wise = WiseProvider()
    wise._create_quote = wise._create_unauthenticated_quote
    result = wise.get_quote(amount=None, source_currency="USD", destination_currency="EUR")
    wise.close()

    if not result["success"]:
        logger.info(f"✅ SUCCESS: Properly handled missing amount")
        logger.info(f"  Error: {result['error_message']}")
    else:
        logger.info(f"❌ FAILED: Did not properly handle missing amount")

    # Test missing currency
    logger.info("\nTesting missing currency:")
    wise = WiseProvider()
    wise._create_quote = wise._create_unauthenticated_quote
    result = wise.get_quote(amount=Decimal("100"), source_currency="USD", destination_currency=None)
    wise.close()

    if not result["success"]:
        logger.info(f"✅ SUCCESS: Properly handled missing currency")
        logger.info(f"  Error: {result['error_message']}")
    else:
        logger.info(f"❌ FAILED: Did not properly handle missing currency")

    # Test get_exchange_rate method
    logger.info("\n===== Testing get_exchange_rate method =====")
    try:
        wise = WiseProvider()
        wise._create_quote = wise._create_unauthenticated_quote

        result = wise.get_exchange_rate(
            send_amount=Decimal("100"), send_currency="USD", receive_currency="EUR"
        )
        wise.close()

        if result["success"]:
            logger.info(f"✅ SUCCESS: get_exchange_rate working properly")
            logger.info(f"  Exchange rate: {result['exchange_rate']}")
            logger.info(f"  Fee: {result['fee']}")
        else:
            logger.info(f"❌ FAILED: get_exchange_rate failed")
            logger.info(f"  Error: {result['error_message']}")

    except Exception as e:
        logger.error(f"get_exchange_rate test error: {str(e)}")


def main():
    """Main function to run the tests."""
    parser = argparse.ArgumentParser(description="Test Wise aggregator functionality")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Use live API with authentication (requires WISE_API_KEY)",
    )
    parser.add_argument(
        "--direct", action="store_true", help="Use direct mode with unauthenticated API"
    )
    args = parser.parse_args()

    if args.live:
        run_tests(use_live_api=True)
    elif args.direct:
        run_tests(use_live_api=False)
    else:
        logger.error("Please specify either --live or --direct mode")
        logger.error("Example: python -m apps.providers.wise.test_aggregator --direct")
        sys.exit(1)


if __name__ == "__main__":
    main()
