#!/usr/bin/env python3
"""
Test script to verify the get_exchange_rate method of the OrbitRemit provider.
"""

import sys
from decimal import Decimal

# Import the OrbitRemit provider
from apps.providers.orbitremit.integration import OrbitRemitProvider

def main():
    provider = OrbitRemitProvider()
    
    # Test cases for different country/currency pairs
    test_cases = [
        {"send_amount": Decimal("1000"), "send_currency": "AUD", "receive_country": "PH"},
        {"send_amount": Decimal("500"), "send_currency": "NZD", "receive_country": "IN"},
        {"send_amount": Decimal("200"), "send_currency": "GBP", "receive_country": "BD"},
        {"send_amount": Decimal("300"), "send_currency": "EUR", "receive_country": "LK"},
        {"send_amount": Decimal("1500"), "send_currency": "USD", "receive_country": "VN"},
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}/{len(test_cases)}: {test_case['send_amount']} {test_case['send_currency']} to {test_case['receive_country']}")
        
        result = provider.get_exchange_rate(**test_case)
        
        if result and result.get("success"):
            print(f"✅ Success: {test_case['send_amount']} {test_case['send_currency']} → {result.get('target_currency')}")
            print(f"   Fee: {result.get('fee')}")
            print(f"   Rate: {result.get('rate')}")
            print(f"   Target amount: {result.get('target_amount')}")
        else:
            error = "Unknown error" if not result else result.get("error_message", "Unknown error")
            print(f"❌ Failed: {error}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 