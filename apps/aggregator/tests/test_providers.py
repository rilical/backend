"""
Test file to verify the functionality of all nine providers with the aggregator.

This script tests the aggregator with all nine providers (including newly added
XoomProvider, SingXProvider, and PaysendProvider) on a single corridor
to verify that they're working correctly.
"""

import os
import sys
import logging
import time
from decimal import Decimal
from pprint import pprint

# Add the parent directory to path to allow imports
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from apps.aggregator.aggregator import Aggregator

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def test_all_providers():
    """
    Test all nine providers on a single corridor.
    """
    print("\n\nTesting with all nine providers:")
    print("Original six: XE, Remitly, RIA, Wise, TransferGo, Western Union")
    print("New additions: Xoom, SingX, and Paysend")
    
    print("=" * 80)
    print("TESTING ALL PROVIDERS (9 TOTAL)")
    print("=" * 80)
    
    # Print the providers being tested
    provider_names = [p.__class__.__name__ for p in Aggregator.PROVIDERS]
    print(f"Providers: {', '.join(provider_names)}")
    print(f"Original 6: XEAggregatorProvider, RemitlyProvider, RIAProvider, WiseProvider, TransferGoProvider, WesternUnionProvider")
    print(f"Newly added 3: XoomProvider, SingXProvider, PaysendProvider")
    
    # Test parameters
    source_country = "US"
    dest_country = "IN"
    source_currency = "USD"
    dest_currency = "INR"
    amount = Decimal("1000.00")
    
    print(f"\nCorridor: {source_currency} to {dest_currency} ({source_country} to {dest_country})")
    print(f"Amount: {amount} {source_currency}")
    
    # Run the test
    start_time = time.time()
    result = Aggregator.get_all_quotes(
        source_country=source_country,
        dest_country=dest_country,
        source_currency=source_currency,
        dest_currency=dest_currency,
        amount=amount,
        sort_by="best_rate"
    )
    elapsed = time.time() - start_time
    
    print(f"\nTest completed in {elapsed:.2f} seconds")
    print(f"Success: {result['success']}")
    
    # Print provider results
    all_providers = result.get('all_providers', [])
    success_count = sum(1 for p in all_providers if p.get('success', False))
    fail_count = len(all_providers) - success_count
    
    print(f"Providers: {len(all_providers)} total, {success_count} successful, {fail_count} failed")
    
    # Print successful providers
    if result.get('quotes'):
        print("\nSuccessful Providers:")
        for i, quote in enumerate(result.get('quotes', []), 1):
            provider = quote.get('provider_id', 'Unknown')
            rate = quote.get('exchange_rate')
            fee = quote.get('fee')
            dest_amount = quote.get('destination_amount')
            delivery_time = quote.get('delivery_time_minutes')
            
            print(f"{i}. {provider}:")
            print(f"   Rate: {rate}")
            print(f"   Fee: {fee}")
            print(f"   Recipient Gets: {dest_amount}")
            print(f"   Delivery Time: {delivery_time} minutes")
            print()
    
    # Print failed providers
    failed_providers = [p for p in all_providers if not p.get('success', False)]
    if failed_providers:
        print("\nFailed Providers:")
        for i, provider in enumerate(failed_providers, 1):
            provider_id = provider.get('provider_id', 'Unknown')
            error = provider.get('error_message', 'Unknown error')
            
            print(f"{i}. {provider_id}: {error}")
    
    print("=" * 80)

if __name__ == "__main__":
    test_all_providers() 