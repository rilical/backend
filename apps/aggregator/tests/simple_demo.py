#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RemitScout Simple Demo
======================

A simplified demonstration of how the RemitScout aggregator works.
"""

import os
import sys
import logging
from decimal import Decimal
from tabulate import tabulate

# Set up path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('remitscout_demo')

# Import components
from apps.aggregator.aggregator import Aggregator
from apps.aggregator.configurator import AggregatorConfig

def print_banner(text):
    """Print a banner with the given text."""
    print("\n" + "=" * len(text))
    print(text)
    print("=" * len(text) + "\n")

def demo_basic_comparison():
    """Demonstrate a basic comparison of remittance providers."""
    print_banner("DEMO 1: Basic Comparison - US to India (USD to INR)")
    
    print("Setting up the aggregator...")
    agg = Aggregator()
    
    # Configure the aggregator
    config = AggregatorConfig()
    config.disable_provider("PangeaProvider")
    config.disable_provider("MukuruProvider")
    config.disable_provider("DahabshiilProvider")
    config.disable_provider("WireBarleyProvider")
    config.set_default_max_workers(3)
    config.set_default_timeout(20)
    
    print(f"Getting quotes for 1000 USD from US to India...")
    result = agg.get_quotes(
        send_amount=Decimal("1000.00"),
        source_country="US",
        destination_country="IN",
        source_currency="USD",
        destination_currency="INR"
    )
    
    if result['success']:
        quotes = result['quotes']
        print(f"Success! Found {len(quotes)} quotes.")
        
        # Prepare data for tabulate
        table_data = []
        for quote in quotes:
            table_data.append([
                quote['provider_name'],
                f"{float(quote['exchange_rate']):.4f}" if quote['exchange_rate'] else "N/A",
                f"{float(quote['fee']):.2f}" if quote['fee'] is not None else "N/A",
                f"{float(quote['recipient_gets']):.2f}" if quote['recipient_gets'] else "N/A",
                f"{int(quote['delivery_time_minutes']) / 60:.1f} hrs" if quote['delivery_time_minutes'] else "Unknown",
                quote.get('payment_method', 'N/A')
            ])
        
        # Print results
        print(tabulate(
            table_data,
            headers=["Provider", "Rate", "Fee", "Recipient Gets", "Delivery Time", "Payment Method"],
            tablefmt="grid"
        ))
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")

def demo_lowest_fee():
    """Demonstrate finding the provider with the lowest fee."""
    print_banner("DEMO 2: Finding Lowest Fee - US to India (USD to INR)")
    
    print("Setting up the aggregator...")
    agg = Aggregator()
    
    # Configure the aggregator for lowest fee
    config = AggregatorConfig()
    config.disable_provider("PangeaProvider")
    config.disable_provider("MukuruProvider")
    config.disable_provider("DahabshiilProvider")
    config.disable_provider("WireBarleyProvider")
    config.set_default_max_workers(3)
    config.set_default_timeout(20)
    config.set_default_sort("lowest_fee")
    
    print(f"Getting quotes for 1000 USD from US to India, sorted by lowest fee...")
    result = agg.get_quotes(
        send_amount=Decimal("1000.00"),
        source_country="US",
        destination_country="IN",
        source_currency="USD",
        destination_currency="INR"
    )
    
    if result['success']:
        quotes = result['quotes']
        print(f"Success! Found {len(quotes)} quotes.")
        
        # Prepare data for tabulate
        table_data = []
        for quote in quotes:
            table_data.append([
                quote['provider_name'],
                f"{float(quote['exchange_rate']):.4f}" if quote['exchange_rate'] else "N/A",
                f"{float(quote['fee']):.2f}" if quote['fee'] is not None else "N/A",
                f"{float(quote['recipient_gets']):.2f}" if quote['recipient_gets'] else "N/A",
                f"{int(quote['delivery_time_minutes']) / 60:.1f} hrs" if quote['delivery_time_minutes'] else "Unknown",
                quote.get('payment_method', 'N/A')
            ])
        
        # Print results
        print(tabulate(
            table_data,
            headers=["Provider", "Rate", "Fee", "Recipient Gets", "Delivery Time", "Payment Method"],
            tablefmt="grid"
        ))
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")

def demo_different_corridor():
    """Demonstrate comparing a different corridor."""
    print_banner("DEMO 3: Different Corridor - US to Mexico (USD to MXN)")
    
    print("Setting up the aggregator...")
    agg = Aggregator()
    
    # Configure the aggregator
    config = AggregatorConfig()
    config.disable_provider("PangeaProvider")
    config.disable_provider("MukuruProvider")
    config.disable_provider("DahabshiilProvider")
    config.disable_provider("WireBarleyProvider")
    config.set_default_max_workers(3)
    config.set_default_timeout(20)
    
    print(f"Getting quotes for 500 USD from US to Mexico...")
    result = agg.get_quotes(
        send_amount=Decimal("500.00"),
        source_country="US",
        destination_country="MX",
        source_currency="USD",
        destination_currency="MXN"
    )
    
    if result['success']:
        quotes = result['quotes']
        print(f"Success! Found {len(quotes)} quotes.")
        
        # Prepare data for tabulate
        table_data = []
        for quote in quotes:
            table_data.append([
                quote['provider_name'],
                f"{float(quote['exchange_rate']):.4f}" if quote['exchange_rate'] else "N/A",
                f"{float(quote['fee']):.2f}" if quote['fee'] is not None else "N/A",
                f"{float(quote['recipient_gets']):.2f}" if quote['recipient_gets'] else "N/A",
                f"{int(quote['delivery_time_minutes']) / 60:.1f} hrs" if quote['delivery_time_minutes'] else "Unknown",
                quote.get('payment_method', 'N/A')
            ])
        
        # Print results
        print(tabulate(
            table_data,
            headers=["Provider", "Rate", "Fee", "Recipient Gets", "Delivery Time", "Payment Method"],
            tablefmt="grid"
        ))
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")

def main():
    """Run the demos."""
    print_banner("REMITSCOUT AGGREGATOR DEMONSTRATION")
    
    # List available providers
    config = AggregatorConfig()
    print("Available providers:")
    providers = config.get_all_available_providers()
    for provider in providers:
        if provider not in ["PangeaProvider", "MukuruProvider", "DahabshiilProvider", "WireBarleyProvider"]:
            print(f"- {provider}")
    
    # Run demos
    try:
        demo_basic_comparison()
        demo_lowest_fee()
        demo_different_corridor()
    except Exception as e:
        print(f"Error during demonstration: {str(e)}")
    
    print_banner("DEMONSTRATION COMPLETE")

if __name__ == "__main__":
    main() 