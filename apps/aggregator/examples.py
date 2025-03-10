"""
Usage examples for the RemitScout Aggregator.

This module provides practical examples of how to use the RemitScout Aggregator
with various filtering and sorting options.
"""

import logging
import sys
from decimal import Decimal
from tabulate import tabulate

from apps.aggregator.aggregator import Aggregator
from apps.aggregator.filters import (
    create_min_exchange_rate_filter,
    create_max_fee_filter,
    create_max_delivery_time_filter,
    create_providers_include_filter,
    create_providers_exclude_filter,
    create_payment_method_filter,
    create_custom_filter,
    combine_filters
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

def format_results(result):
    """Format aggregator results in a table for display."""
    if not result.get("success", False):
        print("No quotes found matching criteria.")
        return

    headers = ["Provider", "Rate", "Fee", "Recipient Gets", "Delivery Time (hours)", "Payment Method"]
    table_data = []
    
    for quote in result.get("quotes", []):
        if quote.get("success", False):
            provider_id = quote.get("provider_id", "Unknown")
            exchange_rate = quote.get("exchange_rate", "N/A")
            fee = quote.get("fee", "N/A")
            dest_amount = quote.get("destination_amount", "N/A")
            delivery_time = "N/A"
            if quote.get("delivery_time_minutes") is not None:
                delivery_time = f"{quote.get('delivery_time_minutes') / 60:.1f}"
            payment_method = quote.get("payment_method", "N/A")
            
            table_data.append([
                provider_id,
                exchange_rate,
                fee,
                dest_amount,
                delivery_time,
                payment_method
            ])
    
    print("\nMatching Quotes:")
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    print(f"\nTotal quotes: {len(table_data)}")
    print(f"Execution time: {result.get('elapsed_seconds', 0):.2f} seconds")
    
    # Print applied filters
    filters = result.get("filters_applied", {})
    print("\nFilters Applied:")
    for key, value in filters.items():
        print(f"  {key}: {value}")


def example_1_basic_usage():
    """Basic usage of the aggregator with default sorting (best rate)."""
    print("\n=== Example 1: Basic Usage (Default Sort by Best Rate) ===\n")
    
    result = Aggregator.get_all_quotes(
        source_country="US",
        dest_country="IN",
        source_currency="USD",
        dest_currency="INR",
        amount=Decimal("1000.00")
    )
    
    format_results(result)


def example_2_sort_by_lowest_fee():
    """Sort quotes by lowest fee."""
    print("\n=== Example 2: Sort by Lowest Fee ===\n")
    
    result = Aggregator.get_all_quotes(
        source_country="US",
        dest_country="IN",
        source_currency="USD",
        dest_currency="INR",
        amount=Decimal("1000.00"),
        sort_by="lowest_fee"
    )
    
    format_results(result)


def example_3_sort_by_fastest_delivery():
    """Sort quotes by fastest delivery time."""
    print("\n=== Example 3: Sort by Fastest Delivery Time ===\n")
    
    result = Aggregator.get_all_quotes(
        source_country="US",
        dest_country="IN",
        source_currency="USD",
        dest_currency="INR",
        amount=Decimal("1000.00"),
        sort_by="fastest_time"
    )
    
    format_results(result)


def example_4_exclude_providers():
    """Exclude specific providers from the results."""
    print("\n=== Example 4: Exclude Specific Providers ===\n")
    
    result = Aggregator.get_all_quotes(
        source_country="US",
        dest_country="IN",
        source_currency="USD",
        dest_currency="INR",
        amount=Decimal("1000.00"),
        exclude_providers=["XoomProvider", "PaysendProvider"]
    )
    
    format_results(result)


def example_5_max_fee_filter():
    """Filter quotes by maximum fee."""
    print("\n=== Example 5: Maximum Fee Filter ===\n")
    
    result = Aggregator.get_all_quotes(
        source_country="US",
        dest_country="IN",
        source_currency="USD",
        dest_currency="INR",
        amount=Decimal("1000.00"),
        max_fee=5.0  # Only include quotes with fee <= $5.00
    )
    
    format_results(result)


def example_6_max_delivery_time():
    """Filter quotes by maximum delivery time."""
    print("\n=== Example 6: Maximum Delivery Time Filter ===\n")
    
    result = Aggregator.get_all_quotes(
        source_country="US",
        dest_country="IN",
        source_currency="USD",
        dest_currency="INR",
        amount=Decimal("1000.00"),
        max_delivery_time_minutes=2880  # 48 hours
    )
    
    format_results(result)


def example_7_min_exchange_rate():
    """Filter quotes by minimum exchange rate using custom filter."""
    print("\n=== Example 7: Minimum Exchange Rate Filter ===\n")
    
    min_rate_filter = create_min_exchange_rate_filter(86.0)
    
    result = Aggregator.get_all_quotes(
        source_country="US",
        dest_country="IN",
        source_currency="USD",
        dest_currency="INR",
        amount=Decimal("1000.00"),
        filter_fn=min_rate_filter
    )
    
    format_results(result)


def example_8_combined_filters():
    """Combine multiple filters."""
    print("\n=== Example 8: Combined Filters ===\n")
    
    # Create individual filters
    min_rate_filter = create_min_exchange_rate_filter(85.0)
    max_fee_filter = create_max_fee_filter(10.0)
    max_time_filter = create_max_delivery_time_filter(4320)  # 72 hours
    
    # Combine them
    combined_filter = combine_filters(min_rate_filter, max_fee_filter, max_time_filter)
    
    result = Aggregator.get_all_quotes(
        source_country="US",
        dest_country="IN",
        source_currency="USD",
        dest_currency="INR",
        amount=Decimal("1000.00"),
        filter_fn=combined_filter,
        sort_by="best_rate"
    )
    
    format_results(result)


def example_9_custom_filter_builder():
    """Use the custom filter builder for convenient filtering."""
    print("\n=== Example 9: Custom Filter Builder ===\n")
    
    custom_filter = create_custom_filter(
        min_rate=85.0,
        max_fee=10.0,
        max_delivery_time=4320,  # 72 hours
        exclude_providers=["SingXProvider"]
    )
    
    result = Aggregator.get_all_quotes(
        source_country="US",
        dest_country="IN",
        source_currency="USD",
        dest_currency="INR",
        amount=Decimal("1000.00"),
        filter_fn=custom_filter,
        sort_by="best_value"  # Use the custom scoring algorithm
    )
    
    format_results(result)


def example_10_different_corridor():
    """Test with a different corridor (US to Mexico)."""
    print("\n=== Example 10: Different Corridor (US to Mexico) ===\n")
    
    result = Aggregator.get_all_quotes(
        source_country="US",
        dest_country="MX",
        source_currency="USD",
        dest_currency="MXN",
        amount=Decimal("500.00")
    )
    
    format_results(result)


if __name__ == "__main__":
    print("RemitScout Aggregator Examples")
    print("==============================")
    
    # Run examples
    example_1_basic_usage()
    example_2_sort_by_lowest_fee()
    example_3_sort_by_fastest_delivery()
    example_4_exclude_providers()
    example_5_max_fee_filter()
    example_6_max_delivery_time()
    example_7_min_exchange_rate()
    example_8_combined_filters()
    example_9_custom_filter_builder()
    example_10_different_corridor() 