#!/usr/bin/env python3
"""
Command Line Interface for the RemitScout Aggregator.

This module provides a CLI tool to run the RemitScout Aggregator and view results.
"""

import sys
import logging
import argparse
import json
from decimal import Decimal
from tabulate import tabulate

from apps.aggregator.aggregator import Aggregator
from apps.aggregator.filters import create_custom_filter


def setup_logging(level=logging.INFO):
    """Configure logging for the CLI."""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )


def format_table(result):
    """Format the results as a table."""
    if not result.get("success", False):
        return "No quotes found matching criteria."

    headers = ["Provider", "Rate", "Fee", "Recipient Gets", "Delivery (hours)", "Payment Method"]
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
    
    table = tabulate(table_data, headers=headers, tablefmt="grid")
    stats = f"\nTotal quotes: {len(table_data)}"
    stats += f"\nExecution time: {result.get('elapsed_seconds', 0):.2f} seconds"
    
    return table + stats


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="RemitScout Aggregator - Compare remittance quotes across providers"
    )

    # Required arguments
    parser.add_argument(
        "--source-country", "-sc",
        required=True,
        help="Source country (ISO-2 code, e.g., 'US')"
    )
    parser.add_argument(
        "--dest-country", "-dc",
        required=True,
        help="Destination country (ISO-2 code, e.g., 'IN')"
    )
    parser.add_argument(
        "--source-currency", "-scurr",
        required=True,
        help="Source currency (ISO-3 code, e.g., 'USD')"
    )
    parser.add_argument(
        "--dest-currency", "-dcurr",
        required=True,
        help="Destination currency (ISO-3 code, e.g., 'INR')"
    )
    parser.add_argument(
        "--amount", "-a",
        required=True,
        type=float,
        help="Amount to send in source currency"
    )

    # Optional arguments
    parser.add_argument(
        "--sort-by", "-s",
        choices=["best_rate", "lowest_fee", "fastest_time", "best_value"],
        default="best_rate",
        help="How to sort the results (default: best_rate)"
    )
    parser.add_argument(
        "--exclude", "-e",
        nargs="+",
        help="List of provider IDs to exclude (e.g., 'XoomProvider')"
    )
    parser.add_argument(
        "--max-fee", "-mf",
        type=float,
        help="Maximum fee (in source currency)"
    )
    parser.add_argument(
        "--max-delivery-time", "-mdt",
        type=int,
        help="Maximum delivery time (in minutes)"
    )
    parser.add_argument(
        "--min-rate", "-mr",
        type=float,
        help="Minimum exchange rate"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output results as JSON"
    )
    parser.add_argument(
        "--max-workers", "-mw",
        type=int,
        default=10,
        help="Maximum number of concurrent provider calls"
    )
    parser.add_argument(
        "--payment-methods", "-pm",
        nargs="+",
        help="Filter by payment methods (e.g., 'bank account' 'debit card')"
    )
    parser.add_argument(
        "--delivery-methods", "-dm",
        nargs="+",
        help="Filter by delivery methods (e.g., 'bank deposit' 'cash pickup')"
    )
    
    return parser.parse_args()


def main():
    """Main CLI entry point."""
    args = parse_arguments()
    
    # Setup logging based on verbosity
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(log_level)
    
    # Create custom filter if any filter arguments are provided
    filter_fn = None
    if any([args.min_rate, args.max_fee, args.max_delivery_time, args.payment_methods, args.delivery_methods]):
        filter_fn = create_custom_filter(
            min_rate=args.min_rate,
            max_fee=args.max_fee,
            max_delivery_time=args.max_delivery_time,
            payment_methods=args.payment_methods,
            delivery_methods=args.delivery_methods
        )
    
    # Call the aggregator
    result = Aggregator.get_all_quotes(
        source_country=args.source_country,
        dest_country=args.dest_country,
        source_currency=args.source_currency,
        dest_currency=args.dest_currency,
        amount=Decimal(str(args.amount)),
        sort_by=args.sort_by,
        exclude_providers=args.exclude,
        max_workers=args.max_workers,
        filter_fn=filter_fn,
        max_delivery_time_minutes=args.max_delivery_time,
        max_fee=args.max_fee
    )
    
    # Output the results
    if args.json:
        # For JSON output, convert Decimal objects to float
        print(json.dumps(result, indent=2, default=lambda x: float(x) if isinstance(x, Decimal) else x))
    else:
        # Print a summary of the request
        print(f"\nRemitScout Aggregator Results")
        print(f"============================")
        print(f"Sending {args.amount} {args.source_currency} from {args.source_country} to {args.dest_country} in {args.dest_currency}")
        
        # Format and print the table
        print(format_table(result))
        
        # Print applied filters
        filters = result.get("filters_applied", {})
        print("\nFilters Applied:")
        for key, value in filters.items():
            print(f"  {key}: {value}")
        
        # Print error summary if any failures
        errors = {k: v for k, v in result.items() if isinstance(v, dict) and not v.get("success", True)}
        if errors:
            print("\nProvider Errors:")
            for provider_id, error in errors.items():
                print(f"  {provider_id}: {error.get('error_message', 'Unknown error')}")


if __name__ == "__main__":
    main() 