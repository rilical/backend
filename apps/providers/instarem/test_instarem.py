#!/usr/bin/env python
"""
InstaRem Provider Test Script

This script tests the InstaRem integration by fetching quotes for various corridors.
"""

import logging
import sys
from decimal import Decimal

from apps.providers.instarem.integration import InstaRemProvider
from apps.providers.instarem.exceptions import InstaRemApiError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
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
            dest_currency="PHP"
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
                Decimal("90000.00"),
                "USD",
                "PHP",
                "US",
                "PH",
                ["BankDeposit", "InstantTransfer", "PesoNet"]
            ),
            (
                Decimal("100000.00"),
                "USD",
                "INR",
                "US",
                "IN",
                ["BankDeposit", "InstantTransfer"]
            ),
            (
                Decimal("1000.00"),
                "USD",
                "SGD",
                "US",
                "SG",
                ["BankDeposit"]
            ),
        ]

        for amount, source_currency, dest_currency, source_country, dest_country, delivery_methods in test_cases:
            logger.info(f"\nTesting quotes for {source_country} to {dest_country}...")
            
            # First test without specific delivery method
            quote = provider.get_quote(
                amount=amount,
                source_currency=source_currency,
                dest_currency=dest_currency,
                source_country=source_country,
                dest_country=dest_country
            )

            # Log the results regardless of success
            logger.info(f"Available delivery methods: {quote['available_delivery_methods']}")
            logger.info(f"Available payment methods: {quote['available_payment_methods']}")
            if not quote["success"]:
                logger.info(f"Quote failed: {quote['error_message']}")
                continue

            # Verify quote structure
            assert "send_amount" in quote, "Quote should have send amount"
            assert "receive_amount" in quote, "Quote should have receive amount"
            assert "exchange_rate" in quote, "Quote should have exchange rate"
            assert "fee" in quote, "Quote should have fee"
            assert "delivery_time_minutes" in quote, "Quote should have delivery time"
            assert "raw_response" in quote, "Quote should include raw response"

            # Then test specific delivery methods
            for delivery_method in delivery_methods:
                logger.info(f"\nTesting {delivery_method}...")
                quote = provider.get_quote(
                    amount=amount,
                    source_currency=source_currency,
                    dest_currency=dest_currency,
                    source_country=source_country,
                    dest_country=dest_country,
                    delivery_method=delivery_method
                )
                
                if quote["success"]:
                    logger.info(f"Quote successful: Rate={quote['exchange_rate']}, "
                              f"Fee={quote['fee']}, "
                              f"Send={quote['send_amount']}, "
                              f"Receive={quote['receive_amount']}, "
                              f"Delivery Time={quote['delivery_time_minutes']} minutes")
                else:
                    logger.info(f"Quote failed: {quote['error_message']}")

def test_invalid_delivery_method():
    """Test handling of invalid delivery method."""
    with InstaRemProvider() as provider:
        quote = provider.get_quote(
            amount=Decimal("1000.00"),
            source_currency="USD",
            dest_currency="PHP",
            source_country="US",
            dest_country="PH",
            delivery_method="InvalidMethod"
        )
        assert not quote["success"], "Quote should fail with invalid delivery method"
        assert quote["error_message"], "Should have error message"

if __name__ == "__main__":
    logger.info("=== Testing InstaRem Integration ===")
    logger.info("\nTesting delivery methods...")
    test_delivery_methods()
    logger.info("\nTesting quotes...")
    test_quotes()
    logger.info("\nTesting invalid delivery method...")
    test_invalid_delivery_method() 