#!/usr/bin/env python
"""
Test script for the Aggregator class.

This script tests the Aggregator with a single corridor to verify functionality.
"""

import os
import sys
import logging
import time
from decimal import Decimal
from pprint import pprint

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('aggregator_test')

# Import the Aggregator class
from apps.aggregator.aggregator import Aggregator

def main():
    """Test a single corridor to verify the aggregator is working."""
    print("\nTesting USD to INR corridor...\n")
    
    start_time = time.time()
    
    # Call the aggregator with a single corridor
    result = Aggregator.get_all_quotes(
        source_country="US",
        dest_country="IN",
        source_currency="USD",
        dest_currency="INR",
        amount=Decimal("1000.00"),
        sort_by="best_rate",
        max_workers=5
    )
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"Test completed in {duration:.2f} seconds\n")
    
    # Get success and failure counts
    success_count = sum(1 for quote in result["results"] if quote.get("success"))
    fail_count = len(result["results"]) - success_count
    
    print(f"Overall Success: {result['success']}")
    print(f"Providers: {len(result['results'])} total, {success_count} successful, {fail_count} failed\n")
    
    # Print successful quotes
    print("Successful Quotes:")
    for quote in [q for q in result["results"] if q.get("success")]:
        print(f"- {quote.get('provider_id', 'Unknown')}:")
        print(f"  Rate: {quote.get('exchange_rate', 0):.4f}")
        print(f"  Fee: {quote.get('fee', 0):.2f} USD")
        print(f"  Recipient Gets: {quote.get('destination_amount', 0):.2f} INR")
        print(f"  Delivery Time: {quote.get('delivery_time_minutes', 'N/A')} minutes")
        print()
    
    # Print failed providers
    print("Failed Providers:")
    for quote in [q for q in result["results"] if not q.get("success")]:
        print(f"- {quote.get('provider_id', 'Unknown')}: {quote.get('error_message', 'Unknown error')}")

if __name__ == "__main__":
    main() 