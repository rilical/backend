#!/usr/bin/env python3
"""
Test script for Remitly provider integration.
"""

import json
import logging
import os
import sys
from decimal import Decimal
from typing import Any, Dict, List

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from apps.providers.remitly.integration import RemitlyProvider

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("test_remitly")

# Test corridors organized by source currency
TEST_CORRIDORS = {
    # USD corridors
    "USD": [
        {"name": "USD → Philippines (PHP)", "country": "PH", "currency": "PHP"},
        {"name": "USD → India (INR)", "country": "IN", "currency": "INR"},
        {"name": "USD → Mexico (MXN)", "country": "MX", "currency": "MXN"},
        {"name": "USD → Colombia (COP)", "country": "CO", "currency": "COP"},
        {"name": "USD → El Salvador (USD)", "country": "SV", "currency": "USD"},
    ],
    # EUR corridors (using Spain as source country)
    "EUR": [
        {"name": "EUR → Morocco (MAD)", "country": "MA", "currency": "MAD"},
        {"name": "EUR → Philippines (PHP)", "country": "PH", "currency": "PHP"},
        {"name": "EUR → India (INR)", "country": "IN", "currency": "INR"},
    ],
    # GBP corridors
    "GBP": [
        {"name": "GBP → India (INR)", "country": "IN", "currency": "INR"},
        {"name": "GBP → Nigeria (NGN)", "country": "NG", "currency": "NGN"},
        {"name": "GBP → Pakistan (PKR)", "country": "PK", "currency": "PKR"},
    ],
    # CAD corridors
    "CAD": [
        {"name": "CAD → Philippines (PHP)", "country": "PH", "currency": "PHP"},
        {"name": "CAD → India (INR)", "country": "IN", "currency": "INR"},
    ],
    # AUD corridors
    "AUD": [
        {"name": "AUD → Philippines (PHP)", "country": "PH", "currency": "PHP"},
        {"name": "AUD → India (INR)", "country": "IN", "currency": "INR"},
        {"name": "AUD → Vietnam (VND)", "country": "VN", "currency": "VND"},
    ],
    # Unsupported sources/destinations (expected to fail)
    "UNSUPPORTED": [
        {
            "name": "JPY → South Africa (ZAR)",
            "source": "JPY",
            "country": "ZA",
            "currency": "ZAR",
        },
        {
            "name": "EUR → Fiji (FJD)",
            "source": "EUR",
            "country": "FJ",
            "currency": "FJD",
        },
    ],
}

# Source country mapping
SOURCE_COUNTRY_MAP = {
    "USD": "US",
    "EUR": "ES",  # Using Spain for EUR
    "GBP": "GB",
    "CAD": "CA",
    "AUD": "AU",
    "JPY": "JP",
}


def test_get_quote():
    """Test getting quotes for a wide range of corridors"""
    with RemitlyProvider() as provider:
        logger.info("===== Testing quotes for various corridors =====")

        # Test all supported corridors by source currency
        for source_currency, corridors in TEST_CORRIDORS.items():
            if source_currency != "UNSUPPORTED":
                source_country = SOURCE_COUNTRY_MAP[source_currency]

                logger.info(
                    f"\n----- Testing {source_currency} corridors from {source_country} -----"
                )
                for corridor in corridors:
                    logger.info(f"Testing {corridor['name']} (expected to succeed)")

                    try:
                        result = provider.get_quote(
                            amount=Decimal("500"),
                            source_currency=source_currency,
                            dest_currency=corridor["currency"],
                            source_country=source_country,
                            dest_country=corridor["country"],
                        )

                        # Log key information from the result
                        if result["success"]:
                            logger.info(
                                f"SUCCESS: {source_currency} → {corridor['currency']} | "
                                f"Rate: {result.get('exchange_rate')} | "
                                f"Fee: {result.get('fee')} | "
                                f"Delivery method: {result.get('delivery_method')}"
                            )
                        else:
                            logger.info(f"FAILED: {result.get('error_message')}")
                    except Exception as e:
                        logger.error(f"ERROR testing {corridor['name']}: {str(e)}")

        # Test unsupported corridors
        logger.info("\n----- Testing unsupported corridors (expected to fail) -----")
        for corridor in TEST_CORRIDORS["UNSUPPORTED"]:
            logger.info(f"Testing {corridor['name']} (expected to fail)")
            source_currency = corridor.get("source", "JPY")
            source_country = SOURCE_COUNTRY_MAP.get(source_currency, "JP")

            try:
                result = provider.get_quote(
                    amount=Decimal("500"),
                    source_currency=source_currency,
                    dest_currency=corridor["currency"],
                    source_country=source_country,
                    dest_country=corridor["country"],
                )
                logger.info(
                    f"Result: {'SUCCESS' if result['success'] else 'FAILED'} - {result.get('error_message', 'No error message')}"
                )
            except Exception as e:
                logger.error(f"ERROR testing {corridor['name']}: {str(e)}")


def test_get_exchange_rate():
    """Test the exchange rate method with different corridors"""
    with RemitlyProvider() as provider:
        logger.info("\n===== Testing exchange rates for various corridors =====")

        # Sample a few corridors to test exchange rates
        test_cases = [
            {"name": "USD → PHP", "source": "USD", "target": "PHP", "country": "PH"},
            {"name": "EUR → INR", "source": "EUR", "target": "INR", "country": "IN"},
            {"name": "GBP → NGN", "source": "GBP", "target": "NGN", "country": "NG"},
            {"name": "CAD → PHP", "source": "CAD", "target": "PHP", "country": "PH"},
        ]

        for test in test_cases:
            logger.info(f"Testing {test['name']} exchange rate")
            try:
                result = provider.get_exchange_rate(
                    send_amount=Decimal("500"),
                    send_currency=test["source"],
                    target_currency=test["target"],
                    receive_country=test["country"],
                )

                if result["success"]:
                    logger.info(
                        f"SUCCESS: {test['source']} → {test['target']} | "
                        f"Rate: {result.get('exchange_rate')} | "
                        f"Fee: {result.get('fee')} | "
                        f"Send: {result.get('send_amount')} | "
                        f"Receive: {result.get('destination_amount')}"
                    )
                else:
                    logger.info(f"FAILED: {result.get('error_message')}")
            except Exception as e:
                logger.error(f"ERROR testing {test['name']}: {str(e)}")


def test_support_methods():
    """Test methods that return provider capabilities"""
    with RemitlyProvider() as provider:
        logger.info("\n===== Testing provider capabilities =====")

        # Get supported countries and currencies
        countries = provider.get_supported_countries()
        currencies = provider.get_supported_currencies()

        logger.info(f"Supported countries ({len(countries)}): {', '.join(countries)}")
        logger.info(f"Supported currencies ({len(currencies)}): {', '.join(currencies)}")

        # Test currency mapping for different country formats
        sample_countries = ["PH", "IN", "MX", "CO", "SV"]
        logger.info("\nTesting currency mapping:")
        for country in sample_countries:
            logger.info(f"Currency for {country}: {provider._get_currency_for_country(country)}")
            logger.info(
                f"Currency for {provider._convert_country_code(country)}: {provider._get_currency_for_country(provider._convert_country_code(country))}"
            )

        # Test country code conversion
        sample_country_codes = ["US", "GB", "ES", "CA", "AU", "IN", "PH"]
        logger.info("\nTesting country code conversion:")
        for code in sample_country_codes:
            logger.info(f"{code} → {provider._convert_country_code(code)}")

        # Test delivery method normalization
        delivery_methods = [
            "BANK_DEPOSIT",
            "CASH_PICKUP",
            "HOME_DELIVERY",
            "MOBILE_WALLET",
        ]
        logger.info("\nTesting delivery method normalization:")
        for method in delivery_methods:
            logger.info(f"{method} → {provider._normalize_delivery_method(method)}")


if __name__ == "__main__":
    logger.info("Starting Remitly provider comprehensive tests...")
    logger.info("Note: Using live API calls with no mock data")

    # Run comprehensive tests
    test_get_quote()
    test_get_exchange_rate()
    test_support_methods()

    logger.info("Tests completed!")
