#!/usr/bin/env python3
"""
Test script for the aggregator-ready Rewire provider.

This script tests the Rewire provider implementation with no fallback data.
If API calls fail, the provider should return a standardized response with
success=False and an appropriate error message.

Example usage:
    python3 -m apps.providers.rewire.tests
"""

import sys
import logging
from decimal import Decimal
from typing import Dict, Any

from apps.providers.rewire.integration import RewireProvider
from apps.providers.rewire.exceptions import (
    RewireError,
    RewireConnectionError,
    RewireResponseError
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("rewire_test")

# Test corridors to check
TEST_CORRIDORS = [
    # Common working corridors (expected to succeed)
    {"name": "IL → Philippines (PHP)", "source": "IL", "currency": "ILS", "dest": "PH", "dest_curr": "PHP"},
    {"name": "IL → India (INR)", "source": "IL", "currency": "ILS", "dest": "IN", "dest_curr": "INR"},
    {"name": "GB → Philippines (PHP)", "source": "GB", "currency": "GBP", "dest": "PH", "dest_curr": "PHP"},
    {"name": "DE → India (INR)", "source": "DE", "currency": "EUR", "dest": "IN", "dest_curr": "INR"},
    
    # Additional corridors from Israel (IL)
    {"name": "IL → Nigeria (NGN)", "source": "IL", "currency": "ILS", "dest": "NG", "dest_curr": "NGN"},
    {"name": "IL → China (CNY)", "source": "IL", "currency": "ILS", "dest": "CN", "dest_curr": "CNY"},
    {"name": "IL → Thailand (THB)", "source": "IL", "currency": "ILS", "dest": "TH", "dest_curr": "THB"},
    {"name": "IL → Kenya (KES)", "source": "IL", "currency": "ILS", "dest": "KE", "dest_curr": "KES"},
    {"name": "IL → Nepal (NPR)", "source": "IL", "currency": "ILS", "dest": "NP", "dest_curr": "NPR"},
    {"name": "IL → Ukraine (UAH)", "source": "IL", "currency": "ILS", "dest": "UA", "dest_curr": "UAH"},
    
    # Likely unsupported corridors (expected to fail)
    {"name": "US → China (CNY)", "source": "US", "currency": "USD", "dest": "CN", "dest_curr": "CNY"},
    {"name": "JP → Brazil (BRL)", "source": "JP", "currency": "JPY", "dest": "BR", "dest_curr": "BRL"},
    
    # Special cases
    {"name": "IL to Invalid currency", "source": "IL", "currency": "ILS", "dest": "XX", "dest_curr": "XYZ"},
]


def format_result(result: Dict[str, Any], test_name: str) -> str:
    """Format a result dictionary for display."""
    if result.get("success", False):
        return (
            f"{test_name}:\n"
            f"  SUCCESS: {result.get('send_amount')} {result.get('source_currency')} → "
            f"{result.get('destination_amount')} {result.get('destination_currency')}\n"
            f"  Rate: {result.get('exchange_rate')}, Fee: {result.get('fee')}\n"
            f"  Delivery: {result.get('delivery_method')}"
        )
    else:
        return (
            f"{test_name}:\n"
            f"  FAILED: {result.get('error_message')}\n"
            f"  {result.get('send_amount')} {result.get('source_currency')} → "
            f"{result.get('destination_currency')}"
        )


def test_get_quote():
    """Test the get_quote method with various corridors."""
    logger.info("=== Testing get_quote method ===")
    
    with RewireProvider() as provider:
        for corridor in TEST_CORRIDORS:
            try:
                logger.info(f"Testing: {corridor['name']}")
                result = provider.get_quote(
                    amount=Decimal("500"),
                    source_currency=corridor["currency"],
                    dest_currency=corridor["dest_curr"],
                    source_country=corridor["source"],
                    dest_country=corridor["dest"]
                )
                
                # Display formatted result
                print(format_result(result, corridor["name"]))
                print("-" * 50)
                
            except RewireError as e:
                logger.error(f"Error testing {corridor['name']}: {e}")
                print(f"{corridor['name']}: ERROR - {str(e)}")
                print("-" * 50)


def test_get_exchange_rate():
    """Test the get_exchange_rate method with various corridors."""
    logger.info("=== Testing get_exchange_rate method ===")
    
    with RewireProvider() as provider:
        # Test a few working corridors
        working_corridors = TEST_CORRIDORS[:3]  # First 3 are expected to work
        
        for corridor in working_corridors:
            try:
                logger.info(f"Testing: {corridor['name']}")
                result = provider.get_exchange_rate(
                    send_amount=Decimal("750"),
                    send_country=corridor["source"],
                    send_currency=corridor["currency"],
                    receive_currency=corridor["dest_curr"]
                )
                
                # Display formatted result
                print(format_result(result, corridor["name"]))
                print("-" * 50)
                
            except RewireError as e:
                logger.error(f"Error testing {corridor['name']}: {e}")
                print(f"{corridor['name']}: ERROR - {str(e)}")
                print("-" * 50)


def test_provider_details():
    """Test provider capabilities and utilities."""
    logger.info("=== Testing provider capabilities ===")
    
    with RewireProvider() as provider:
        # Test supported countries
        countries = provider.get_supported_countries()
        logger.info(f"Supported countries: {', '.join(countries)}")
        
        # Test supported currencies
        currencies = provider.get_supported_currencies()
        logger.info(f"Supported currencies: {', '.join(currencies)}")
        
        # Test corridor support
        for corridor in TEST_CORRIDORS[:4]:  # First 4 should be supported
            supported = provider.is_corridor_supported(
                corridor["source"], 
                corridor["dest"]
            )
            logger.info(f"Corridor {corridor['source']} → {corridor['dest']}: {'Supported' if supported else 'Not supported'}")


def test_error_handling():
    """Test the provider's behavior when given invalid inputs or when API calls fail."""
    logger.info("=== Testing error handling ===")
    
    with RewireProvider() as provider:
        # Test invalid source country
        try:
            logger.info("Testing invalid source country")
            result = provider.get_quote(
                amount=Decimal("500"),
                source_currency="XYZ",
                dest_currency="PHP",
                source_country="XX",
                dest_country="PH"
            )
            print(format_result(result, "Invalid source country"))
            print("-" * 50)
        except Exception as e:
            logger.error(f"Unexpected error with invalid source country: {e}")
            
        # Test invalid amount
        try:
            logger.info("Testing with invalid amount (-500)")
            result = provider.get_quote(
                amount=Decimal("-500"),
                source_currency="ILS",
                dest_currency="PHP",
                source_country="IL",
                dest_country="PH"
            )
            print(format_result(result, "Invalid amount"))
            print("-" * 50)
        except Exception as e:
            logger.error(f"Unexpected error with invalid amount: {e}")
    

def main():
    """Run all tests."""
    logger.info("Starting Rewire provider tests...")
    logger.info("NOTE: This implementation uses NO FALLBACK DATA.")
    logger.info("If API calls fail, the provider returns errors instead of mock data.")
    
    test_get_quote()
    test_get_exchange_rate()
    test_provider_details()
    test_error_handling()
    
    logger.info("Tests completed!")


if __name__ == "__main__":
    main() 