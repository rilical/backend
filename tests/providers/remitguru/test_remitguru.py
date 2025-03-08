#!/usr/bin/env python3
"""
Test script for RemitGuru integration.

This script tests the RemitGuru integration by making a test request
to get exchange rates for different corridors.
"""

import os
import sys
import json
import logging
from decimal import Decimal

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from apps.providers.remitguru.integration import RemitGuruProvider

def test_get_exchange_rate():
    """Test getting exchange rates from RemitGuru."""
    provider = RemitGuruProvider()
    
    # Define test cases - based on the curl command that worked
    test_cases = [
        {
            "send_amount": Decimal("7800"),
            "send_currency": "GBP",
            "receive_country": "IN",
            "description": "GBP to INR (from example that works)"
        },
        {
            "send_amount": Decimal("1000"),
            "send_currency": "GBP",
            "receive_country": "PH",
            "description": "GBP to PHP"
        },
        {
            "send_amount": Decimal("1000"),
            "send_currency": "GBP",
            "receive_country": "PK",
            "description": "GBP to PKR"
        },
        {
            "send_amount": Decimal("5000"),
            "send_currency": "USD",
            "receive_country": "IN",
            "description": "USD to INR"
        }
    ]
    
    print("Testing RemitGuru API integration...\n")
    
    # Run tests
    for test_case in test_cases:
        print(f"\n{'='*50}")
        print(f"Testing {test_case['description']}:")
        print(f"Send amount: {test_case['send_amount']} {test_case['send_currency']}")
        print(f"To country: {test_case['receive_country']}")
        print(f"{'-'*50}")
        
        try:
            # Test the get_quote method directly first
            print("1. Testing get_quote method...")
            
            # Determine send_country from currency
            send_country = None
            for country, currency in provider.CURRENCY_MAPPING.items():
                if currency == test_case['send_currency']:
                    send_country = country
                    break
            
            if not send_country:
                print(f"❌ Could not determine send country for currency {test_case['send_currency']}")
                continue
                
            quote = provider.get_quote(
                send_amount=test_case['send_amount'],
                send_country=send_country,
                receive_country=test_case['receive_country']
            )
            
            if not quote:
                print("❌ Failed to get quote")
                continue
                
            if not quote.get('is_valid', False):
                print(f"❌ Quote returned is invalid: {quote.get('error', 'Unknown error')}")
                print(f"Raw response: {quote.get('raw_response')}")
                continue
                
            print(f"✅ Receive amount: {quote['receive_amount']} {quote['receive_currency']}")
            print(f"✅ Exchange rate: {quote['exchange_rate']}")
            print(f"✅ Fee: {quote['fee']} {quote['send_currency']}")
            print(f"✅ Is valid: {quote['is_valid']}")
            
            # Now test the full exchange rate method
            print("\n2. Testing get_exchange_rate method...")
            result = provider.get_exchange_rate(
                send_amount=test_case['send_amount'],
                send_currency=test_case['send_currency'],
                receive_country=test_case['receive_country']
            )
            
            if not result:
                print("❌ Failed to get exchange rate")
                continue
                
            if not result.get('supported', False):
                print(f"❌ Corridor not supported: {result.get('error', 'Unknown error')}")
                continue
            
            print(f"✅ Exchange rate: {result['exchange_rate']}")
            print(f"✅ Receive amount: {result['receive_amount']} {result['receive_currency']}")
            print(f"✅ Fee: {result['fee']} {test_case['send_currency']}")
            print(f"✅ Delivery time: {result['delivery_time']} hours")
            
            # Print raw response for debugging
            if result.get('raw_json') and result['raw_json'].get('raw_response'):
                print(f"\nRaw API response: {result['raw_json']['raw_response']}")
            
        except Exception as e:
            print(f"❌ Error occurred: {str(e)}")

if __name__ == "__main__":
    test_get_exchange_rate() 