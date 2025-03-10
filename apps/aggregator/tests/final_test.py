#!/usr/bin/env python
"""
Final test script for the fully functional aggregator.

This script tests the aggregator with all three providers:
- XEAggregatorProvider (with fixed integration)
- RemitlyProvider
- RIAProvider
"""

import os
import sys
import logging
import time
from decimal import Decimal
from tabulate import tabulate

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Import the aggregator
from apps.aggregator.aggregator import Aggregator

# Test parameters
TEST_PARAMS = {
    "source_country": "US",
    "dest_country": "IN",
    "source_currency": "USD",
    "dest_currency": "INR",
    "amount": Decimal("1000.00")
}

def run_aggregator_test():
    """
    Run a complete test of the aggregator.
    """
    print("\n" + "=" * 80)
    print("RUNNING COMPLETE AGGREGATOR TEST")
    print("=" * 80)
    
    # List active providers
    provider_names = [getattr(p, "name", p.__class__.__name__) for p in Aggregator.PROVIDERS]
    print(f"\nTesting with providers: {', '.join(provider_names)}")
    
    # Run the aggregator
    print(f"\nTesting corridor: US to IN (USD to INR)")
    print(f"Amount: {TEST_PARAMS['amount']} {TEST_PARAMS['source_currency']}")
    
    start_time = time.time()
    
    result = Aggregator.get_all_quotes(
        source_country=TEST_PARAMS["source_country"],
        dest_country=TEST_PARAMS["dest_country"],
        source_currency=TEST_PARAMS["source_currency"],
        dest_currency=TEST_PARAMS["dest_currency"],
        amount=TEST_PARAMS["amount"],
        sort_by="best_rate"
    )
    
    duration = time.time() - start_time
    
    # Print results
    print(f"\nTest completed in {duration:.2f} seconds")
    print(f"Aggregator success: {result['success']}")
    
    # Count successes and failures
    success_count = sum(1 for r in result["results"] if r.get("success"))
    fail_count = len(result["results"]) - success_count
    
    print(f"Providers: {len(result['results'])} total, {success_count} successful, {fail_count} failed")
    
    # Create table for display
    table_data = []
    for i, quote in enumerate(result["results"], 1):
        provider_id = quote.get("provider_id", "Unknown")
        success = quote.get("success", False)
        
        if success:
            table_data.append([
                i,
                provider_id,
                "✓",
                f"{quote.get('exchange_rate', 0):.4f}",
                f"{quote.get('fee', 0):.2f}",
                f"{quote.get('destination_amount', 0):.2f}",
                f"{quote.get('delivery_time_minutes', 'N/A')} min"
            ])
        else:
            error = quote.get("error_message", "Unknown error")
            table_data.append([
                i,
                provider_id,
                "✗",
                "N/A",
                "N/A",
                "N/A",
                error
            ])
    
    headers = ["#", "Provider", "Success", "Rate", "Fee", "Recipient Gets", "Delivery Time/Error"]
    print("\n" + tabulate(table_data, headers=headers, tablefmt="pipe"))
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    run_aggregator_test() 