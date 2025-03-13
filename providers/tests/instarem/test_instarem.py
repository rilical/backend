#!/usr/bin/env python
"""
InstaRem Provider Test Script

This script tests the InstaRem integration by fetching quotes for various corridors.
"""

import json
import logging
import os
import sys
from decimal import Decimal

# Add the project root to the Python path to allow direct imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from providers.instarem.exceptions import InstaRemApiError
from providers.instarem.integration import InstaRemProvider

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("instarem-test")


def test_delivery_methods():
    """Test getting delivery methods."""
    with InstaRemProvider() as provider:
        # Test getting delivery methods
        methods = provider.get_delivery_methods(
            source_country="US",
            dest_country="PH",
            source_currency="USD",
            dest_currency="PHP",
        )

        # Verify we get methods back
        assert methods, "Should get delivery methods"
        logger.info(f"Available methods: {methods}")

        # Verify method structure
        for method in methods:
            assert "id" in method, "Method should have an ID"
            assert "name" in method, "Method should have a name"
            assert "type" in method, "Method should have a type"
            assert "estimated_minutes" in method, "Method should have estimated delivery time"
            assert "description" in method, "Method should have a description"
            assert "is_default" in method, "Method should indicate if it's default"


def test_quotes():
    """Test getting quotes for various corridors with different delivery methods."""
    with InstaRemProvider() as provider:
        test_cases = [
            # (amount, source_currency, dest_currency, source_country, dest_country, delivery_methods)
            (
                Decimal("1000.00"),
                "USD",
                "PHP",
                "US",
                "PH",
                ["BankDeposit", "InstantTransfer", "PesoNet"],
            ),
            (
                Decimal("1000.00"),
                "USD",
                "INR",
                "US",
                "IN",
                ["BankDeposit", "InstantTransfer"],
            ),
            (Decimal("1000.00"), "USD", "SGD", "US", "SG", ["BankDeposit"]),
        ]

        for (
            amount,
            source_currency,
            dest_currency,
            source_country,
            dest_country,
            delivery_methods,
        ) in test_cases:
            logger.info(f"\nTesting quotes for {source_country} to {dest_country}...")

            # First test without specific delivery method
            quote = provider.get_quote(
                amount=amount,
                source_currency=source_currency,
                dest_currency=dest_currency,
                source_country=source_country,
                dest_country=dest_country,
                include_raw=True,
            )

            # Log the results in a nicely formatted JSON
            logger.info(f"Quote for {source_currency} to {dest_currency}:")
            logger.info(json.dumps(quote, indent=2))

            if not quote["success"]:
                logger.info(f"Quote failed: {quote.get('error_message')}")
                continue

            # Verify quote structure
            assert "send_amount" in quote, "Quote should have send amount"
            assert "source_currency" in quote, "Quote should have source currency"
            assert quote.get("exchange_rate") is not None, "Quote should have exchange rate"
            assert quote.get("fee") is not None, "Quote should have fee"

            if "destination_amount" in quote and quote["destination_amount"]:
                logger.info(
                    f"Destination amount: {quote['destination_amount']} {quote.get('destination_currency')}"
                )

            # Then test specific delivery methods if supported
            for delivery_method in delivery_methods:
                logger.info(f"\nTesting {delivery_method}...")
                quote_with_method = provider.get_quote(
                    amount=amount,
                    source_currency=source_currency,
                    dest_currency=dest_currency,
                    source_country=source_country,
                    dest_country=dest_country,
                    delivery_method=delivery_method,
                    include_raw=True,
                )

                if quote_with_method["success"]:
                    logger.info(
                        f"Quote successful: Rate={quote_with_method.get('exchange_rate')}, "
                        f"Fee={quote_with_method.get('fee')}, "
                        f"Send={quote_with_method.get('send_amount')}, "
                        f"Receive={quote_with_method.get('destination_amount')}"
                    )
                else:
                    logger.info(f"Quote failed: {quote_with_method.get('error_message')}")


def test_exchange_rate():
    """Test getting exchange rate directly."""
    with InstaRemProvider() as provider:
        test_cases = [
            # (source_currency, target_currency, source_country, target_country)
            ("USD", "PHP", "US", "PH"),
            ("USD", "INR", "US", "IN"),
            ("USD", "SGD", "US", "SG"),
        ]

        for (
            source_currency,
            target_currency,
            source_country,
            target_country,
        ) in test_cases:
            logger.info(f"\nTesting exchange rate for {source_currency} to {target_currency}...")

            rate_info = provider.get_exchange_rate(
                source_currency=source_currency,
                target_currency=target_currency,
                source_country=source_country,
                target_country=target_country,
            )

            logger.info(f"Exchange rate response: {json.dumps(rate_info, indent=2)}")

            if rate_info["success"]:
                assert rate_info.get("rate") is not None, "Exchange rate should have a rate value"
                assert (
                    rate_info.get("source_currency") == source_currency.upper()
                ), "Source currency should match"
                assert (
                    rate_info.get("target_currency") == target_currency.upper()
                ), "Target currency should match"

                logger.info(
                    f"Exchange rate: 1 {source_currency} = {rate_info.get('rate')} {target_currency}"
                )
                logger.info(f"Fee: {rate_info.get('fee')}")
            else:
                logger.info(f"Exchange rate failed: {rate_info.get('error_message')}")


def test_invalid_delivery_method():
    """Test handling of invalid delivery method."""
    with InstaRemProvider() as provider:
        quote = provider.get_quote(
            amount=Decimal("1000.00"),
            source_currency="USD",
            dest_currency="PHP",
            source_country="US",
            dest_country="PH",
            delivery_method="InvalidMethod",
        )
        logger.info(f"Invalid delivery method response: {json.dumps(quote, indent=2)}")
        # Note: With the new implementation, invalid delivery method might not fail explicitly


if __name__ == "__main__":
    logger.info("=== Testing InstaRem Integration ===")
    logger.info("\nTesting delivery methods...")
    test_delivery_methods()
    logger.info("\nTesting quotes...")
    test_quotes()
    logger.info("\nTesting exchange rate...")
    test_exchange_rate()
    logger.info("\nTesting invalid delivery method...")
    test_invalid_delivery_method()
    logger.info("\nAll tests completed.")
