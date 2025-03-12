#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RemitScout Command Line Interface
=================================

A simple CLI for the RemitScout aggregator that allows users to:
1. Compare rates across providers for specific corridors
2. Configure which providers to include/exclude
3. Set filters for fees, delivery time, etc.
"""

import argparse
import json
import logging
import os
import sys
from decimal import Decimal

from tabulate import tabulate

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("remitscout_cli")

# Import aggregator components
from apps.aggregator.aggregator import Aggregator
from apps.aggregator.configurator import AggregatorConfig, get_configured_aggregator_params


def parse_arguments():
    """Parse command-line arguments for RemitScout CLI."""
    parser = argparse.ArgumentParser(description="RemitScout CLI - Compare remittance providers")

    # Required parameters
    parser.add_argument("--amount", type=float, help="Amount to send")
    parser.add_argument("--from-country", help="Source country code (e.g., US)")
    parser.add_argument("--to-country", help="Destination country code (e.g., MX)")
    parser.add_argument("--from-currency", help="Source currency code (e.g., USD)")
    parser.add_argument("--to-currency", help="Destination currency code (e.g., MXN)")

    # Optional filters
    parser.add_argument(
        "--sort-by",
        choices=["best_rate", "lowest_fee", "fastest_time"],
        default="best_rate",
        help="How to sort results",
    )
    parser.add_argument("--max-fee", type=float, help="Maximum fee (in source currency)")
    parser.add_argument("--max-delivery-time", type=int, help="Maximum delivery time (in hours)")

    # Provider selection
    parser.add_argument(
        "--list-providers", action="store_true", help="List all available providers"
    )
    parser.add_argument("--include-only", help="Comma-separated list of providers to include")
    parser.add_argument("--exclude-providers", help="Comma-separated list of providers to exclude")

    # Output format
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    parser.add_argument("--output-file", help="Save output to specified file")

    return parser.parse_args()


def configure_aggregator(args):
    """Configure the aggregator based on command-line args."""
    from apps.aggregator.aggregator import Aggregator

    agg = Aggregator()

    # Configure provider inclusion/exclusion
    if args.include_only:
        providers_to_include = [p.strip() for p in args.include_only.split(",")]
        agg.include_only_providers(providers_to_include)

    if args.exclude_providers:
        providers_to_exclude = [p.strip() for p in args.exclude_providers.split(",")]
        agg.exclude_providers(providers_to_exclude)

    # Configure sorting
    if args.sort_by == "lowest_fee":
        agg.sort_by_lowest_fee()
    elif args.sort_by == "fastest_time":
        agg.sort_by_fastest_delivery()
    else:  # Default to best_rate
        agg.sort_by_best_rate()

    # Configure filters
    filters = {}
    if args.max_fee is not None:
        filters["max_fee"] = Decimal(str(args.max_fee))

    if args.max_delivery_time is not None:
        filters["max_delivery_time_minutes"] = args.max_delivery_time * 60

    if filters:
        agg.set_filters(filters)

    return agg


def list_available_providers():
    """List all available providers in the system."""
    from apps.aggregator.aggregator import Aggregator

    agg = Aggregator()
    providers = agg.list_all_providers()
    return providers


def format_output(result, json_output=False, output_file=None):
    """Format the output according to specified parameters."""
    if json_output:
        formatted_output = json.dumps(result, indent=2, default=str)
    else:
        # Create tabular output
        if not result.get("quotes"):
            formatted_output = "No quotes found matching your criteria."
        else:
            table_data = []
            for quote in result.get("quotes", []):
                row = [
                    quote.get("provider_name"),
                    f"{quote.get('source_amount')} {quote.get('source_currency')}",
                    f"{quote.get('destination_amount')} {quote.get('destination_currency')}",
                    f"{quote.get('exchange_rate'):.4f}",
                    f"{quote.get('fee')} {quote.get('source_currency')}",
                    f"{quote.get('delivery_time_minutes') // 60}h"
                    if quote.get("delivery_time_minutes")
                    else "Unknown",
                ]
                table_data.append(row)

            headers = ["Provider", "Send", "Receive", "Rate", "Fee", "Time"]
            formatted_output = tabulate(table_data, headers=headers, tablefmt="grid")

            # Add summary info
            formatted_output += f"\n\nSearch: {result.get('source_amount')} {result.get('source_currency')} → {result.get('destination_currency')}"
            formatted_output += (
                f"\nFrom: {result.get('source_country')} To: {result.get('destination_country')}"
            )
            formatted_output += f"\nQuotes found: {len(result.get('quotes', []))}"
            formatted_output += (
                f"\nSorted by: {result.get('filters_applied', {}).get('sort_by', 'best_rate')}"
            )

    # Output to file if specified
    if output_file:
        with open(output_file, "w") as f:
            f.write(formatted_output)
        print(f"Results saved to {output_file}")

    return formatted_output


def main():
    """Main function for the RemitScout CLI."""
    args = parse_arguments()

    # Just list providers and exit if requested
    if args.list_providers:
        providers = list_available_providers()
        print("\nAvailable Providers:")
        for idx, provider in enumerate(providers, 1):
            print(f"{idx}. {provider}")
        return

    # Ensure we have all required parameters
    required_params = [
        "amount",
        "from_country",
        "to_country",
        "from_currency",
        "to_currency",
    ]
    missing_params = [
        p.replace("_", "-") for p in required_params if getattr(args, p.lower()) is None
    ]

    if missing_params:
        print(f"Error: Missing required parameters: {', '.join(missing_params)}")
        print("Use --help for usage information")
        sys.exit(1)

    # Configure and run the aggregator
    agg = configure_aggregator(args)

    try:
        result = agg.get_quotes(
            source_country=args.from_country,
            destination_country=args.to_country,
            source_currency=args.from_currency,
            destination_currency=args.to_currency,
            source_amount=Decimal(str(args.amount)),
        )

        # Format and display the results
        formatted_output = format_output(result, args.json, args.output_file)
        print(formatted_output)

    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
