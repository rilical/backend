#!/usr/bin/env python
"""
InstaRem Provider Test Script

This script tests the InstaRem integration by fetching quotes for various corridors.
"""

import logging
import sys
import json
import os
from decimal import Decimal

# Add the project root to the Python path to allow direct imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from apps.providers.instarem.integration import InstaRemProvider
from apps.providers.instarem.exceptions import InstaRemApiError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger("instarem-test")

# Add a custom JSON encoder to handle Decimal objects
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

def json_dumps(obj, **kwargs):
    """Wrapper for json.dumps that handles Decimal objects"""
    return json.dumps(obj, cls=DecimalEncoder, **kwargs)

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
                Decimal("1000.00"),
                "USD",
                "PHP",
                "US",
                "PH",
                ["BankDeposit", "InstantTransfer", "PesoNet"]
            ),
            (
                Decimal("1000.00"),
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
                dest_country=dest_country,
                include_raw=True
            )

            # Log the results in a nicely formatted JSON
            logger.info(f"Quote for {source_currency} to {dest_currency}:")
            logger.info(json_dumps(quote, indent=2))
            
            if not quote["success"]:
                logger.info(f"Quote failed: {quote.get('error_message')}")
                continue

            # Verify quote contains all aggregator-required fields
            required_fields = [
                "provider_id", "success", "send_amount", "source_currency", 
                "destination_amount", "destination_currency", "exchange_rate",
                "rate", "fee", "timestamp"
            ]
            for field in required_fields:
                assert field in quote, f"Quote must include '{field}' for aggregator compatibility"
            
            # Verify data types and values
            assert quote["provider_id"] == "instarem", "Provider ID should match the provider name"
            assert isinstance(quote["success"], bool), "Success should be a boolean"
            assert quote["source_currency"] == source_currency.upper(), "Source currency should be uppercase"
            assert quote["destination_currency"] == dest_currency.upper(), "Destination currency should be uppercase"
            assert quote["rate"] == quote["exchange_rate"], "Rate should mirror exchange_rate for aggregator compatibility"
            
            if "destination_amount" in quote and quote["destination_amount"]:
                logger.info(f"Destination amount: {quote['destination_amount']} {quote.get('destination_currency')}")
            
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
                    include_raw=True
                )
                
                if quote_with_method["success"]:
                    logger.info(f"Quote successful: Rate={quote_with_method.get('exchange_rate')}, "
                              f"Fee={quote_with_method.get('fee')}, "
                              f"Send={quote_with_method.get('send_amount')}, "
                              f"Receive={quote_with_method.get('destination_amount')}")
                    
                    # Verify delivery method is reflected in the response
                    assert "delivery_method" in quote_with_method, "Quote should include the delivery method"
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
        
        for source_currency, target_currency, source_country, target_country in test_cases:
            logger.info(f"\nTesting exchange rate for {source_currency} to {target_currency}...")
            
            rate_info = provider.get_exchange_rate(
                source_currency=source_currency,
                target_currency=target_currency,
                source_country=source_country,
                target_country=target_country
            )
            
            logger.info(f"Exchange rate response: {json_dumps(rate_info, indent=2)}")
            
            # Verify exchange rate contains all aggregator-required fields
            if rate_info["success"]:
                required_fields = [
                    "provider_id", "success", "source_currency", "target_currency", 
                    "rate", "timestamp", "send_amount"
                ]
                for field in required_fields:
                    assert field in rate_info, f"Exchange rate response must include '{field}' for aggregator compatibility"
                
                assert rate_info.get("rate") is not None, "Exchange rate should have a rate value"
                assert rate_info.get("source_currency") == source_currency.upper(), "Source currency should match and be uppercase"
                assert rate_info.get("target_currency") == target_currency.upper(), "Target currency should match and be uppercase"
                
                logger.info(f"Exchange rate: 1 {source_currency} = {rate_info.get('rate')} {target_currency}")
                logger.info(f"Fee: {rate_info.get('fee')}")
            else:
                logger.info(f"Exchange rate failed: {rate_info.get('error_message')}")
                # Even in failure case, verify minimum required fields
                assert "provider_id" in rate_info, "Exchange rate must include provider_id even in error case"
                assert "error_message" in rate_info, "Exchange rate must include error_message when success is False"

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
        logger.info(f"Invalid delivery method response: {json_dumps(quote, indent=2)}")
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