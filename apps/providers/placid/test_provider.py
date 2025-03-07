"""
Test script for the Placid provider integration.

This script tests the Placid provider to ensure it returns properly
formatted responses according to the aggregator's standardized format.
"""

import sys
import logging
import json
from decimal import Decimal
from pprint import pprint

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Import the provider
from apps.providers.placid.integration import PlacidProvider

def test_get_quote():
    """Test the get_quote method with various currency pairs."""
    print("\n=== Testing PlacidProvider.get_quote() ===\n")
    
    # Initialize the provider
    provider = PlacidProvider()
    
    # Test cases - source_currency, dest_currency, source_country, dest_country
    test_cases = [
        # USD to INR (India)
        ("USD", "INR", "US", "IN"),
        # GBP to PKR (Pakistan)
        ("GBP", "PKR", "GB", "PK"),
        # EUR to BDT (Bangladesh)
        ("EUR", "BDT", "EU", "BD"),
        # Invalid source currency
        ("JPY", "INR", "JP", "IN"),
        # Invalid destination currency
        ("USD", "XYZ", "US", "XX"),
    ]
    
    for source_currency, dest_currency, source_country, dest_country in test_cases:
        print(f"\nTesting: {source_currency} -> {dest_currency} ({source_country} -> {dest_country})")
        
        # Get quote
        quote = provider.get_quote(
            amount=Decimal('1000.00'),
            source_currency=source_currency,
            dest_currency=dest_currency,
            source_country=source_country,
            dest_country=dest_country
        )
        
        # Print formatted result
        print(f"Success: {quote['success']}")
        if quote['success']:
            print(f"Exchange rate: {quote['exchange_rate']}")
            print(f"Send amount: {quote['send_amount']} {quote['source_currency']}")
            print(f"Receive amount: {quote['destination_amount']} {quote['destination_currency']}")
            print(f"Delivery time: {quote['delivery_time_minutes'] / 60} hours")
        else:
            print(f"Error: {quote['error_message']}")
        
        # Verify the response format
        verify_response_format(quote)

def test_get_exchange_rate():
    """Test the legacy get_exchange_rate method."""
    print("\n=== Testing PlacidProvider.get_exchange_rate() ===\n")
    
    # Initialize the provider
    provider = PlacidProvider()
    
    # Test cases - send_currency, target_currency
    test_cases = [
        # USD to INR
        ("USD", "INR"),
        # GBP to PKR
        ("GBP", "PKR"),
    ]
    
    for send_currency, target_currency in test_cases:
        print(f"\nTesting: {send_currency} -> {target_currency}")
        
        # Get exchange rate
        result = provider.get_exchange_rate(
            send_amount=Decimal('1000.00'),
            send_currency=send_currency,
            target_currency=target_currency
        )
        
        # Print formatted result
        print(f"Success: {result['success']}")
        if result['success']:
            print(f"Exchange rate: {result['exchange_rate']}")
            print(f"Send amount: {result['send_amount']} {result['source_currency']}")
            print(f"Receive amount: {result['destination_amount']} {result['destination_currency']}")
        else:
            print(f"Error: {result['error_message']}")
        
        # Verify the response format
        verify_response_format(result)

def test_supported_countries_and_currencies():
    """Test the methods that return supported countries and currencies."""
    print("\n=== Testing supported countries and currencies ===\n")
    
    # Initialize the provider
    provider = PlacidProvider()
    
    # Get supported countries
    countries = provider.get_supported_countries()
    print("Supported countries:")
    print(", ".join(countries))
    
    # Get supported currencies
    currencies = provider.get_supported_currencies()
    print("\nSupported currencies:")
    print(", ".join(currencies))

def verify_response_format(response):
    """Verify that the response follows the standardized format."""
    required_keys = [
        "provider_id", "success", "error_message", 
        "send_amount", "source_currency",
        "destination_amount", "destination_currency",
        "exchange_rate", "fee", 
        "payment_method", "delivery_method", "delivery_time_minutes",
        "timestamp"
    ]
    
    missing_keys = [key for key in required_keys if key not in response]
    
    if missing_keys:
        print(f"WARNING: Response is missing required keys: {', '.join(missing_keys)}")
    else:
        print("Response format is valid ✓")

def main():
    """Run all tests."""
    print("\n=== PLACID PROVIDER TESTS ===\n")
    
    try:
        # Test get_quote
        test_get_quote()
        
        # Test get_exchange_rate
        test_get_exchange_rate()
        
        # Test supported countries and currencies
        test_supported_countries_and_currencies()
        
        print("\n=== ALL TESTS COMPLETED ===\n")
        
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 