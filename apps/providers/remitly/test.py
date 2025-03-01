#!/usr/bin/env python3
"""
Test script for Remitly provider integration.
"""

import json
import logging
import os
import sys
from decimal import Decimal

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from apps.providers.remitly.integration import RemitlyProvider

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_exchange_rate():
    """Test getting exchange rates from Remitly."""
    
    print("="*80)
    print("TESTING REMITLY INTEGRATION")
    print("="*80)
    
    # Example corridors to test with a variety of source countries
    test_cases = [
        # US Corridors (USD)
        {
            "name": "USD to Mexico (MXN)",
            "send_amount": Decimal("500.00"),
            "send_currency": "USD",
            "receive_country": "MX",
            "receive_currency": "MXN"
        },
        {
            "name": "USD to Philippines (PHP)",
            "send_amount": Decimal("300.00"),
            "send_currency": "USD",
            "receive_country": "PH",
            "receive_currency": "PHP"
        },
        {
            "name": "USD to India (INR)",
            "send_amount": Decimal("1000.00"),
            "send_currency": "USD",
            "receive_country": "IN",
            "receive_currency": "INR"
        },
        
        # Euro Corridors (Spain/Germany/France)
        {
            "name": "EUR (Spain) to Morocco (MAD)",
            "send_amount": Decimal("500.00"),
            "send_currency": "EUR",
            "receive_country": "MA",
            "receive_currency": "MAD"
        },
        {
            "name": "EUR (Spain) to Colombia (COP)",
            "send_amount": Decimal("400.00"),
            "send_currency": "EUR",
            "receive_country": "CO",
            "receive_currency": "COP"
        },
        {
            "name": "EUR (Spain) to Algeria (DZD)",
            "send_amount": Decimal("500.00"),
            "send_currency": "EUR",
            "receive_country": "DZ",
            "receive_currency": "DZD"
        },
        
        # UK Corridors (GBP)
        {
            "name": "GBP to Nigeria (NGN)",
            "send_amount": Decimal("600.00"),
            "send_currency": "GBP",
            "receive_country": "NG",
            "receive_currency": "NGN"
        },
        {
            "name": "GBP to India (INR)",
            "send_amount": Decimal("800.00"),
            "send_currency": "GBP",
            "receive_country": "IN",
            "receive_currency": "INR"
        },
        
        # Canadian Corridors (CAD)
        {
            "name": "CAD to Philippines (PHP)",
            "send_amount": Decimal("700.00"),
            "send_currency": "CAD",
            "receive_country": "PH",
            "receive_currency": "PHP"
        },
        
        # Australian Corridors (AUD)
        {
            "name": "AUD to Vietnam (VND)",
            "send_amount": Decimal("500.00"),
            "send_currency": "AUD",
            "receive_country": "VN",
            "receive_currency": "VND"
        }
    ]
    
    # Initialize Remitly provider
    remitly = RemitlyProvider()
    
    # Test each corridor
    for test_case in test_cases:
        print(f"\nTesting: {test_case['name']}")
        print("-"*50)
        
        try:
            result = remitly.get_exchange_rate(
                send_amount=test_case["send_amount"],
                send_currency=test_case["send_currency"],
                receive_country=test_case["receive_country"],
                receive_currency=test_case["receive_currency"]
            )
            
            # Print formatted result
            print(f"Source amount: {result['source_amount']} {result['source_currency']}")
            print(f"Destination amount: {result['destination_amount']} {result['destination_currency']}")
            print(f"Exchange rate: {result['exchange_rate']}")
            print(f"Fee: {result['fee']} {result['source_currency']}")
            print(f"Delivery method: {result['delivery_method']}")
            print(f"Payment method: {result['payment_method']}")
            print(f"Corridor: {result['corridor']}")
            
            # Check if this is fallback data
            if result.get("details", {}).get("is_fallback", False):
                print(f"⚠️ NOTE: Using fallback/estimated rates (API request failed)")
            else:
                print(f"✅ SUCCESS: Using live API rates")
            
            # Print the raw response for debugging if needed
            # print("\nRaw JSON response:")
            # print(json.dumps(result.get("details", {}).get("raw_response", {}), indent=2))
            
        except Exception as e:
            print(f"Error: {e}")
    
    print("\nTest completed.")
    
def test_supported_countries():
    """Test getting supported countries from Remitly."""
    
    print("\n" + "="*80)
    print("TESTING REMITLY SUPPORTED COUNTRIES")
    print("="*80)
    
    # Initialize Remitly provider
    remitly = RemitlyProvider()
    
    # Get and print source countries
    print("\nSupported SOURCE countries:")
    print("-"*50)
    source_countries = remitly.get_source_countries()
    for country in source_countries:
        print(f"{country['country_name']} ({country['country_code']}) - {country['currency_code']}")
    
    # Get and print destination countries (just count for brevity)
    print("\nSupported DESTINATION countries:")
    print("-"*50)
    dest_countries = remitly.get_supported_countries()
    print(f"Total supported destination countries: {len(dest_countries)}")
    
    # Print a sample of destination countries
    print("\nSample of destination countries:")
    for country in dest_countries[:10]:  # Show first 10
        print(f"{country['country_name']} ({country['country_code']}) - {country['currency_code']}")
    
    print("\nTest completed.")

if __name__ == '__main__':
    test_exchange_rate()
    test_supported_countries() 