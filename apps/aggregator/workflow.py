#!/usr/bin/env python3
"""
RemitScout Aggregator Workflow Example.

This script demonstrates a typical workflow for using the RemitScout aggregator 
in a real-world application.
"""

import logging
import sys
from decimal import Decimal
from tabulate import tabulate
import time

from apps.aggregator.aggregator import Aggregator
from apps.aggregator.filters import create_custom_filter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


def print_table(quotes, title=None):
    """Format and print quotes as a table."""
    if title:
        print(f"\n{title}")
        print("=" * len(title))
    
    headers = ["Provider", "Rate", "Fee", "Recipient Gets", "Delivery Time (hours)"]
    table_data = []
    
    for quote in quotes:
        provider_id = quote.get("provider_id", "Unknown")
        exchange_rate = quote.get("exchange_rate", "N/A")
        fee = quote.get("fee", "N/A")
        dest_amount = quote.get("destination_amount", "N/A")
        delivery_time = "N/A"
        if quote.get("delivery_time_minutes") is not None:
            delivery_time = f"{quote.get('delivery_time_minutes') / 60:.1f}"
        
        table_data.append([
            provider_id,
            exchange_rate,
            fee,
            dest_amount,
            delivery_time
        ])
    
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    print(f"Total quotes: {len(table_data)}")


def simulate_user_workflow():
    """Simulate a real-world user workflow with the aggregator."""
    
    # Step 1: User inputs their remittance details
    print("\n--- Step 1: Collect User Remittance Details ---")
    source_country = "US"
    dest_country = "IN"
    source_currency = "USD"
    dest_currency = "INR"
    amount = Decimal("1000.00")
    
    print(f"Sending {amount} {source_currency} from {source_country} to {dest_country} in {dest_currency}")
    
    # Step 2: Get initial quotes with default sorting (best exchange rate)
    print("\n--- Step 2: Get Initial Quotes (Best Rate) ---")
    logger.info("Fetching initial quotes sorted by best exchange rate")
    
    start_time = time.time()
    result = Aggregator.get_all_quotes(
        source_country=source_country,
        dest_country=dest_country,
        source_currency=source_currency,
        dest_currency=dest_currency,
        amount=amount,
        sort_by="best_rate"
    )
    logger.info(f"Initial quotes fetched in {time.time() - start_time:.2f} seconds")
    
    # Display the results
    if result.get("success", False):
        print_table(result.get("quotes", []), "Best Exchange Rate Options")
    else:
        print("No quotes available for this corridor")
        return
    
    # Step 3: User filters by maximum fee
    print("\n--- Step 3: User Filters by Maximum Fee ($10) ---")
    logger.info("Applying fee filter")
    
    fee_filter_result = Aggregator.get_all_quotes(
        source_country=source_country,
        dest_country=dest_country,
        source_currency=source_currency,
        dest_currency=dest_currency,
        amount=amount,
        sort_by="best_rate",
        max_fee=10.0
    )
    
    if fee_filter_result.get("success", False):
        print_table(fee_filter_result.get("quotes", []), "Options with Fee ≤ $10")
    else:
        print("No quotes available with fee ≤ $10")
    
    # Step 4: User filters by delivery time
    print("\n--- Step 4: User Filters by Delivery Time (Max 48 hours) ---")
    logger.info("Applying delivery time filter")
    
    time_filter_result = Aggregator.get_all_quotes(
        source_country=source_country,
        dest_country=dest_country,
        source_currency=source_currency,
        dest_currency=dest_currency,
        amount=amount,
        sort_by="best_rate",
        max_delivery_time_minutes=2880  # 48 hours = 2880 minutes
    )
    
    if time_filter_result.get("success", False):
        print_table(time_filter_result.get("quotes", []), "Options with Delivery Time ≤ 48 hours")
    else:
        print("No quotes available with delivery time ≤ 48 hours")
    
    # Step 5: User combines filters and sorts by fastest time
    print("\n--- Step 5: User Applies Combined Filters and Sorts by Fastest Delivery ---")
    logger.info("Applying combined filters and sorting by fastest delivery")
    
    custom_filter = create_custom_filter(
        min_rate=85.0,  # Minimum acceptable exchange rate
        max_fee=10.0,   # Maximum fee
        max_delivery_time=4320  # 72 hours = 4320 minutes
    )
    
    combined_result = Aggregator.get_all_quotes(
        source_country=source_country,
        dest_country=dest_country,
        source_currency=source_currency,
        dest_currency=dest_currency,
        amount=amount,
        sort_by="fastest_time",  # Now sorting by fastest delivery
        filter_fn=custom_filter
    )
    
    if combined_result.get("success", False):
        print_table(combined_result.get("quotes", []), 
                    "Options with Rate ≥ 85, Fee ≤ $10, Time ≤ 72h (Sorted by Fastest)")
    else:
        print("No quotes available matching all criteria")
    
    # Step 6: User selects a provider (simulate with the first result)
    print("\n--- Step 6: User Selects a Provider ---")
    
    selected_quote = None
    if combined_result.get("quotes", []):
        selected_quote = combined_result["quotes"][0]
        provider_id = selected_quote.get("provider_id", "Unknown")
        rate = selected_quote.get("exchange_rate", "N/A")
        fee = selected_quote.get("fee", "N/A")
        recipient_amount = selected_quote.get("destination_amount", "N/A")
        delivery_time = selected_quote.get("delivery_time_minutes", "N/A")
        if delivery_time != "N/A":
            delivery_time = f"{delivery_time / 60:.1f} hours"
        
        print(f"Selected Provider: {provider_id}")
        print(f"Exchange Rate: {rate}")
        print(f"Fee: ${fee}")
        print(f"Recipient Gets: {recipient_amount} {dest_currency}")
        print(f"Estimated Delivery Time: {delivery_time}")
        print(f"Total Cost: ${float(amount) + float(selected_quote.get('fee', 0)):.2f} {source_currency}")
    else:
        print("No provider available to select")
    
    # Step 7: Summary
    print("\n--- Step 7: Workflow Summary ---")
    print(f"Initial Options: {len(result.get('quotes', []))}")
    print(f"Options with Fee ≤ $10: {len(fee_filter_result.get('quotes', []))}")
    print(f"Options with Delivery ≤ 48h: {len(time_filter_result.get('quotes', []))}")
    print(f"Options with Combined Filters: {len(combined_result.get('quotes', []))}")
    
    if selected_quote:
        print(f"Selected Provider: {selected_quote.get('provider_id', 'Unknown')}")
        savings = 0
        if len(result.get("quotes", [])) > 0:
            # Calculate savings compared to the worst rate
            best_rate = selected_quote.get("exchange_rate", 0)
            worst_quote = min(result.get("quotes", []), key=lambda x: x.get("exchange_rate", 0))
            worst_rate = worst_quote.get("exchange_rate", 0)
            if worst_rate > 0:
                savings = (best_rate - worst_rate) * float(amount)
                print(f"Potential Savings: {savings:.2f} {dest_currency} compared to worst rate")
    
    print("\nWorkflow completed successfully!")


if __name__ == "__main__":
    print("RemitScout Aggregator Workflow Example")
    print("======================================")
    simulate_user_workflow() 