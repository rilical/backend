#!/usr/bin/env python3
"""
Test script to verify the get_quote method of the OrbitRemit provider.
"""

import sys
from decimal import Decimal

# Import the OrbitRemit provider
from apps.providers.orbitremit.integration import OrbitRemitProvider

def main():
    provider = OrbitRemitProvider()
    
    # Test cases for different currency pairs
    test_cases = [
        {"amount": Decimal("1000"), "source_currency": "AUD", "target_currency": "PHP"},
        {"amount": Decimal("500"), "source_currency": "NZD", "target_currency": "INR"},
        {"amount": Decimal("200"), "source_currency": "GBP", "target_currency": "PKR"},
        {"amount": Decimal("300"), "source_currency": "EUR", "target_currency": "LKR"},
        {"amount": Decimal("1500"), "source_currency": "USD", "target_currency": "VND"},
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}/{len(test_cases)}: {test_case['amount']} {test_case['source_currency']} to {test_case['target_currency']}")
        
        result = provider.get_quote(**test_case)
        
        if result["success"]:
            print(f"✅ Quote Success: {test_case['amount']} {test_case['source_currency']} → {result['target_amount']} {test_case['target_currency']}")
            print(f"   Fee: {result['fee']}")
            print(f"   Rate: {result['rate']}")
            print(f"   Source: {result.get('rate_source', 'Not specified')}")
            print(f"   Last Updated: {result.get('rate_timestamp', 'Not specified')}")
        else:
            print(f"❌ Quote Failed: {result.get('error_message')}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 