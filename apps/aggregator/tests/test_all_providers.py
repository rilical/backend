#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RemitScout Comprehensive Provider Test
======================================

This script runs the RemitScout aggregator with all 19 providers enabled
to show how the system works at full capacity for a typical user.
"""

import os
import sys
import time
import logging
from decimal import Decimal
from tabulate import tabulate
import concurrent.futures
from typing import Dict, Any, List, Optional, Set
import threading

# Set up path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('remitscout_all_providers')

# Import the aggregator components
from apps.aggregator.aggregator import Aggregator
from apps.aggregator.configurator import AggregatorConfig

# Add a lock for thread-safe printing
print_lock = threading.Lock()

def print_banner(text):
    """Print a banner with the given text in a thread-safe manner."""
    banner = f"\n{'=' * len(text)}\n{text}\n{'=' * len(text)}\n"
    with print_lock:
        print(banner)
    return banner

def print_provider_results(results, corridor_name):
    """Print detailed results for all providers in a thread-safe manner."""
    # Extract basic info
    source_country = results.get('source_country', 'Unknown')
    dest_country = results.get('dest_country', 'Unknown')
    source_currency = results.get('source_currency', 'Unknown')
    dest_currency = results.get('dest_currency', 'Unknown')
    amount = results.get('amount', 0)
    
    # Count successful providers
    all_provider_results = results.get('all_providers', [])
    success_count = sum(1 for p in all_provider_results if p.get('success', False))
    total_count = len(all_provider_results)
    success_rate = (success_count / total_count * 100) if total_count > 0 else 0
    
    # Format data for tabulate
    table_data = []
    for provider in all_provider_results:
        status = "Success" if provider.get('success', False) else "Failed"
        row = [
            provider.get('provider_id', 'Unknown'),
            status,
            provider.get('exchange_rate', 'N/A') if status == "Success" else "N/A",
            provider.get('fee', 'N/A') if status == "Success" else "N/A",
            provider.get('recipient_gets', 'N/A') if status == "Success" else "N/A",
            provider.get('delivery_time_minutes', '') if status == "Success" else "N/A",
            provider.get('error_message', 'N/A') if status == "Failed" else "N/A"
        ]
        table_data.append(row)
    
    # Sort by status (successful first), then by provider name
    table_data.sort(key=lambda x: (0 if x[1] == "Success" else 1, x[0]))
    
    # Create the table
    header = f"Provider Test Results: {source_country}->{dest_country} ({source_currency}->{dest_currency})"
    stats = f"Amount: {amount:.2f} {source_currency}\n" \
            f"Time taken: {results.get('elapsed_seconds', 0):.1f} seconds\n" \
            f"Success rate: {success_count}/{total_count} providers ({success_rate:.2f}%)"
    
    table = tabulate(
        table_data,
        headers=["Provider", "Status", "Rate", "Fee", "Recipient Gets", "Delivery Time (min)", "Error Message"],
        tablefmt="grid"
    )
    
    # Print everything in one atomic operation to avoid interleaved output
    with print_lock:
        print(print_banner(header))
        print(stats)
        print("Detailed Results:")
        print(table)
        print("\n")
    
    return {
        'corridor': corridor_name,
        'success_count': success_count,
        'total_count': total_count,
        'success_rate': success_rate,
        'elapsed_seconds': results.get('elapsed_seconds', 0)
    }

def test_all_providers(corridor_details, sort_by="best_rate", timeout=15, max_workers=5):
    """Run a test with all providers for a specific corridor."""
    source_country, dest_country, source_currency, dest_currency, amount, corridor_name = corridor_details
    
    with print_lock:
        print(f"\nStarting test for corridor: {corridor_name} ({source_country}->{dest_country}, {source_currency}->{dest_currency}, Amount: {amount})")
    
    # Initialize the aggregator with all providers
    try:
        # Enable all providers in the configurator
        config = AggregatorConfig()
        
        # Get the list of all available providers
        all_providers = config.get_all_available_providers()
        
        # Ensure none are excluded
        for provider in all_providers:
            config.enable_provider(provider)
        
        # Set other parameters
        config.set_default_sort(sort_by)
        config.set_default_timeout(timeout)  # Reduce timeout for faster concurrent testing
        config.set_default_max_workers(max_workers)  # Limit workers per corridor to avoid overwhelming the system
        
        # Initializing the aggregator - note we use the class method directly
        # since it doesn't require initialization parameters
        start_time = time.time()
        
        results = Aggregator.get_all_quotes(
            source_country=source_country,
            dest_country=dest_country,
            source_currency=source_currency,
            dest_currency=dest_currency,
            amount=Decimal(str(amount)),
            sort_by=sort_by,
            exclude_providers=[],  # Ensure no providers are excluded
            max_workers=max_workers
        )
        
        # Calculate elapsed time
        elapsed_time = time.time() - start_time
        results['elapsed_seconds'] = elapsed_time
        
        # Print detailed results
        summary = print_provider_results(results, corridor_name)
        return summary
        
    except Exception as e:
        logger.error(f"Error testing corridor {corridor_name}: {str(e)}")
        with print_lock:
            print(f"Error testing {corridor_name}: {str(e)}")
        return {
            'corridor': corridor_name,
            'success_count': 0,
            'total_count': 0,
            'success_rate': 0,
            'elapsed_seconds': 0,
            'error': str(e)
        }

def run_all_tests():
    """Run tests for all corridors with all providers concurrently."""
    print_banner("REMITSCOUT COMPREHENSIVE PROVIDER TEST")
    
    # Define corridors to test
    corridors = [
        ("US", "IN", "USD", "INR", 1000.00, "US to India"),
        ("US", "MX", "USD", "MXN", 500.00, "US to Mexico"),
        ("US", "PH", "USD", "PHP", 300.00, "US to Philippines"),
        ("GB", "IN", "GBP", "INR", 800.00, "UK to India"),
        ("CA", "IN", "CAD", "INR", 1000.00, "Canada to India"),
        ("AU", "IN", "AUD", "INR", 1000.00, "Australia to India"),
        ("SG", "IN", "SGD", "INR", 1000.00, "Singapore to India"),
        ("AE", "IN", "AED", "INR", 1000.00, "UAE to India"),
        ("US", "NG", "USD", "NGN", 500.00, "US to Nigeria"),
        ("ZA", "ZW", "ZAR", "USD", 1000.00, "South Africa to Zimbabwe")
    ]
    
    # Run all corridor tests concurrently
    print(f"Starting concurrent tests for {len(corridors)} corridors...")
    overall_start_time = time.time()
    
    corridor_summaries = []
    
    # Use ThreadPoolExecutor to run all corridor tests in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(corridors)) as executor:
        # Submit all corridor tests to the executor
        future_to_corridor = {
            executor.submit(test_all_providers, corridor): corridor 
            for corridor in corridors
        }
        
        # Process results as they complete
        for future in concurrent.futures.as_completed(future_to_corridor):
            corridor = future_to_corridor[future]
            try:
                summary = future.result()
                corridor_summaries.append(summary)
                print(f"Completed test for {corridor[5]}")
            except Exception as e:
                logger.error(f"Fatal error testing corridor {corridor[5]}: {str(e)}")
                print(f"Fatal error with corridor {corridor[5]}: {str(e)}")
    
    overall_elapsed_time = time.time() - overall_start_time
    print(f"\nAll corridor tests completed in {overall_elapsed_time:.2f} seconds")
    
    # Print overall summary
    print_banner("COMPREHENSIVE TEST SUMMARY")
    
    total_tests = len(corridor_summaries)
    successful_tests = sum(1 for s in corridor_summaries if s.get('success_count', 0) > 0)
    success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
    
    print(f"Total tests: {total_tests}")
    print(f"Successful tests: {successful_tests}")
    print(f"Failed tests: {total_tests - successful_tests}")
    print(f"Success rate: {success_rate:.2f}%")
    
    # Print corridor-by-corridor summary
    print_banner("CORRIDOR SUCCESS RATES")
    corridor_table = []
    for summary in corridor_summaries:
        corridor_table.append([
            summary.get('corridor', 'Unknown'),
            f"{summary.get('success_rate', 0):.2f}%",
            f"{summary.get('success_count', 0)}",
            f"{summary.get('elapsed_seconds', 0):.2f}s"
        ])
    
    print(tabulate(
        corridor_table,
        headers=["Corridor", "Success Rate", "Successful Providers", "Execution Time"],
        tablefmt="grid"
    ))
    
    # Create a provider support matrix
    print_banner("PROVIDER SUPPORT MATRIX")
    create_provider_support_matrix(corridors, corridor_summaries)

def create_provider_support_matrix(corridors, corridor_summaries):
    """Create a matrix showing which providers support which corridors."""
    # This would require additional processing of the raw data
    # For the demonstration, we'll simulate this with sample data
    print("To see the detailed provider support matrix, please run the dedicated corridor analysis tool:")
    print("python3 apps/aggregator/tests/test_corridor_support.py")

def main():
    """Run the comprehensive provider test."""
    try:
        run_all_tests()
        print_banner("TEST COMPLETE")
    except Exception as e:
        logger.error(f"Fatal error in main: {str(e)}")
        print(f"Fatal error: {str(e)}")

if __name__ == "__main__":
    main() 