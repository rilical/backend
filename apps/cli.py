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

import os
import sys
import argparse
import logging
from decimal import Decimal
import json
from tabulate import tabulate

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('remitscout_cli')

# Import aggregator components
from apps.aggregator.aggregator import Aggregator
from apps.aggregator.configurator import AggregatorConfig, get_configured_aggregator_params

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='RemitScout - Compare remittance rates across providers')
    
    # Required arguments
    parser.add_argument('--amount', type=float, required=True, help='Amount to send')
    parser.add_argument('--from-country', type=str, required=True, help='Source country code (e.g., US)')
    parser.add_argument('--to-country', type=str, required=True, help='Destination country code (e.g., IN)')
    parser.add_argument('--from-currency', type=str, required=True, help='Source currency code (e.g., USD)')
    parser.add_argument('--to-currency', type=str, required=True, help='Destination currency code (e.g., INR)')
    
    # Optional filters
    parser.add_argument('--sort-by', type=str, choices=['best_rate', 'lowest_fee', 'fastest_time'], 
                        default='best_rate', help='How to sort the results')
    parser.add_argument('--max-fee', type=float, help='Maximum fee to consider')
    parser.add_argument('--max-delivery-time', type=int, help='Maximum delivery time in hours')
    parser.add_argument('--exclude-providers', type=str, help='Comma-separated list of providers to exclude')
    parser.add_argument('--include-only', type=str, help='Comma-separated list of providers to include (excludes all others)')
    
    # Output options
    parser.add_argument('--json', action='store_true', help='Output in JSON format')
    parser.add_argument('--output-file', type=str, help='File to save output to')
    
    # Advanced options
    parser.add_argument('--timeout', type=int, default=30, help='Timeout for provider requests in seconds')
    parser.add_argument('--max-workers', type=int, default=5, help='Maximum number of concurrent requests')
    parser.add_argument('--disable-cache', action='store_true', help='Disable caching of results')
    
    # Provider configuration
    parser.add_argument('--list-providers', action='store_true', help='List all available providers and exit')
    parser.add_argument('--save-config', action='store_true', help='Save the current configuration for future use')
    
    return parser.parse_args()

def configure_aggregator(args):
    """Configure the aggregator based on command line arguments."""
    # Create or load configurator
    config = AggregatorConfig()
    
    # Handle provider inclusions/exclusions
    if args.exclude_providers:
        excluded = [p.strip() for p in args.exclude_providers.split(',')]
        for provider in excluded:
            config.disable_provider(provider)
    
    if args.include_only:
        included = [p.strip() for p in args.include_only.split(',')]
        all_providers = config.get_all_available_providers()
        for provider in all_providers:
            if provider not in included:
                config.disable_provider(provider)
    
    # Set default sort
    config.set_default_sort(args.sort_by)
    
    # Set other parameters
    config.set_default_timeout(args.timeout)
    config.set_default_max_workers(args.max_workers)
    
    if args.disable_cache:
        config.enable_caching(False)
    
    # Save configuration if requested
    if args.save_config:
        config._save_config()
        print("Configuration saved for future use.")
    
    # Get parameters for aggregator
    params = config.get_aggregator_params()
    
    # Add command-line specific parameters
    if args.max_fee:
        params['max_fee'] = args.max_fee
    
    if args.max_delivery_time:
        params['max_delivery_time_minutes'] = args.max_delivery_time * 60
    
    return params

def list_available_providers():
    """List all available providers."""
    config = AggregatorConfig()
    config.print_status()
    sys.exit(0)

def format_output(result, json_output=False, output_file=None):
    """Format and display the results."""
    if not result['success']:
        print(f"Error: {result.get('error', 'Unknown error')}")
        return
    
    quotes = result['quotes']
    if not quotes:
        print("No quotes found matching your criteria.")
        return
    
    if json_output:
        output = json.dumps(result, indent=2, default=str)
        if output_file:
            with open(output_file, 'w') as f:
                f.write(output)
        else:
            print(output)
        return
    
    # Format for console output
    table_data = []
    for quote in quotes:
        try:
            row = [
                quote['provider_name'],
                f"{float(quote['exchange_rate']):.4f}" if quote['exchange_rate'] else "N/A",
                f"{float(quote['fee']):.2f}" if quote['fee'] is not None else "N/A",
                f"{float(quote['recipient_gets']):.2f}" if quote['recipient_gets'] else "N/A",
                f"{int(quote['delivery_time_minutes']) / 60:.1f} hrs" if quote['delivery_time_minutes'] else "Unknown",
                quote.get('payment_method', 'N/A')
            ]
            table_data.append(row)
        except Exception as e:
            logger.error(f"Error formatting quote: {e}")
            continue
    
    # Print table
    if table_data:
        table = tabulate(
            table_data,
            headers=["Provider", "Rate", "Fee", "Recipient Gets", "Delivery Time", "Payment Method"],
            tablefmt="grid"
        )
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(table)
        else:
            print(table)
    else:
        print("Failed to format any quotes. Try using --json for raw output.")

def main():
    """Main CLI function."""
    args = parse_arguments()
    
    # Handle special commands
    if args.list_providers:
        list_available_providers()
    
    # Configure aggregator
    params = configure_aggregator(args)
    
    # Initialize aggregator
    aggregator = Aggregator(**params)
    
    # Get quotes
    result = aggregator.get_quotes(
        send_amount=Decimal(str(args.amount)),
        source_country=args.from_country,
        destination_country=args.to_country,
        source_currency=args.from_currency,
        destination_currency=args.to_currency
    )
    
    # Format and display output
    format_output(result, args.json, args.output_file)

if __name__ == '__main__':
    main() 