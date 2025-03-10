#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RemitScout Aggregator - User Workflow Demonstration
===================================================

This script demonstrates how a typical user would use the RemitScout aggregator
to find the best remittance options across multiple scenarios.
"""

import os
import sys
import time
import logging
from decimal import Decimal
from tabulate import tabulate
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# Setup path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('remitscout_demo')

# Import the aggregator and configurator
from apps.aggregator.aggregator import Aggregator
from apps.aggregator.configurator import AggregatorConfig

# Rich console for pretty output
console = Console()

def print_header(title):
    """Print a formatted header."""
    console.print(Panel(Text(title, justify="center"), style="bold blue"))

def print_section(title):
    """Print a section title."""
    console.print(f"\n[bold yellow]{title}[/bold yellow]")
    console.print("=" * len(title))

def run_aggregator_with_config(config_params, amount, source_country, destination_country, 
                              source_currency, destination_currency, scenario_name=None):
    """Run the aggregator with specific configuration parameters."""
    if scenario_name:
        print_section(f"Scenario: {scenario_name}")
    
    console.print(f"[green]Sending [bold]{amount} {source_currency}[/bold] from [bold]{source_country}[/bold] to [bold]{destination_country}[/bold] in [bold]{destination_currency}[/bold][/green]")
    console.print(f"Configuration: {config_params}")
    
    # Add timeout settings if not present
    if 'timeout' not in config_params:
        config_params['timeout'] = 30
    
    # Add max_workers if not present
    if 'max_workers' not in config_params:
        config_params['max_workers'] = 5
    
    # Start timing
    start_time = time.time()
    
    # Create aggregator with parameters
    try:
        aggregator = Aggregator(**config_params)
        
        # Run quote retrieval
        result = aggregator.get_quotes(
            send_amount=Decimal(amount),
            source_country=source_country,
            destination_country=destination_country,
            source_currency=source_currency,
            destination_currency=destination_currency
        )
    except Exception as e:
        console.print(f"[bold red]Error creating aggregator or getting quotes: {str(e)}[/bold red]")
        return {'success': False, 'error': str(e), 'quotes': []}
    
    # Calculate execution time
    execution_time = time.time() - start_time
    
    # Display results
    if result['success']:
        quotes = result['quotes']
        console.print(f"[bold green]✓ Successfully retrieved {len(quotes)} quotes in {execution_time:.2f} seconds[/bold green]")
        
        if quotes:
            # Format data for tabulate
            table_data = []
            for quote in quotes:
                try:
                    rate = f"{quote['exchange_rate']:.4f}" if quote['exchange_rate'] else "N/A"
                    fee = f"{quote['fee']:.2f}" if quote['fee'] is not None else "N/A"
                    amount = f"{quote['recipient_gets']:.2f}" if quote['recipient_gets'] else "N/A"
                    delivery = f"{quote['delivery_time_minutes'] / 60:.1f}" if quote['delivery_time_minutes'] else "Unknown"
                    
                    table_data.append([
                        quote['provider_name'],
                        rate,
                        fee,
                        amount,
                        delivery,
                        quote.get('payment_method', 'N/A')
                    ])
                except Exception as e:
                    logger.error(f"Error formatting quote: {str(e)}")
                    continue
            
            # Print table
            if table_data:
                console.print(tabulate(
                    table_data,
                    headers=["Provider", "Rate", "Fee", "Recipient Gets", "Delivery (hours)", "Payment Method"],
                    tablefmt="grid"
                ))
            else:
                console.print("[bold yellow]Retrieved quotes but couldn't format them correctly.[/bold yellow]")
        else:
            console.print("[bold yellow]No quotes found matching your criteria![/bold yellow]")
    else:
        console.print(f"[bold red]✗ Error retrieving quotes: {result.get('error', 'Unknown error')}[/bold red]")
    
    console.print(f"[italic]Execution time: {execution_time:.2f} seconds[/italic]")
    console.print("")
    
    return result

def scenario_1_basic_comparison():
    """Scenario 1: Basic comparison of all providers."""
    # Use default configuration
    config = AggregatorConfig()
    params = config.get_aggregator_params()
    
    # Set sorting to best rate
    params['sort_by'] = 'best_rate'
    
    return run_aggregator_with_config(
        params, 1000, 'US', 'IN', 'USD', 'INR',
        "Basic Comparison - All Providers (Best Rate)"
    )

def scenario_2_fastest_delivery():
    """Scenario 2: Finding the fastest delivery option."""
    config = AggregatorConfig()
    params = config.get_aggregator_params()
    
    # Set sorting to fastest delivery time
    params['sort_by'] = 'fastest_time'
    
    return run_aggregator_with_config(
        params, 1000, 'US', 'IN', 'USD', 'INR',
        "Finding Fastest Delivery Option"
    )

def scenario_3_lowest_fee():
    """Scenario 3: Finding the lowest fee option."""
    config = AggregatorConfig()
    params = config.get_aggregator_params()
    
    # Set sorting to lowest fee
    params['sort_by'] = 'lowest_fee'
    
    return run_aggregator_with_config(
        params, 1000, 'US', 'IN', 'USD', 'INR',
        "Finding Lowest Fee Option"
    )

def scenario_4_different_corridor():
    """Scenario 4: Testing a different corridor."""
    config = AggregatorConfig()
    params = config.get_aggregator_params()
    
    return run_aggregator_with_config(
        params, 500, 'US', 'MX', 'USD', 'MXN',
        "Different Corridor - US to Mexico"
    )

def scenario_5_exclude_problematic_providers():
    """Scenario 5: Excluding providers that are causing issues."""
    config = AggregatorConfig()
    
    # Disable providers that are known to have issues
    config.disable_provider("PangeaProvider")
    config.disable_provider("MukuruProvider")
    config.disable_provider("DahabshiilProvider")
    config.disable_provider("KoronaPayProvider")
    
    params = config.get_aggregator_params()
    
    return run_aggregator_with_config(
        params, 1000, 'US', 'IN', 'USD', 'INR',
        "Excluding Problematic Providers"
    )

def scenario_6_maximum_fee():
    """Scenario 6: Setting a maximum fee."""
    config = AggregatorConfig()
    params = config.get_aggregator_params()
    
    # Set a maximum fee
    params['max_fee'] = 5.0
    
    return run_aggregator_with_config(
        params, 1000, 'US', 'IN', 'USD', 'INR',
        "Setting Maximum Fee (5.0)"
    )

def scenario_7_maximum_delivery_time():
    """Scenario 7: Setting a maximum delivery time."""
    config = AggregatorConfig()
    params = config.get_aggregator_params()
    
    # Set a maximum delivery time (24 hours)
    params['max_delivery_time_minutes'] = 24 * 60
    
    return run_aggregator_with_config(
        params, 1000, 'US', 'IN', 'USD', 'INR',
        "Setting Maximum Delivery Time (24 hours)"
    )

def scenario_8_different_amount():
    """Scenario 8: Testing with a different amount."""
    config = AggregatorConfig()
    params = config.get_aggregator_params()
    
    return run_aggregator_with_config(
        params, 5000, 'US', 'IN', 'USD', 'INR',
        "Different Amount - 5000 USD"
    )

def scenario_9_prioritize_specific_providers():
    """Scenario 9: Prioritizing specific providers."""
    config = AggregatorConfig()
    
    # Disable all providers except a select few
    available_providers = config.get_all_available_providers()
    priority_providers = ["WiseProvider", "XEAggregatorProvider", "RemitlyProvider"]
    
    for provider in available_providers:
        if provider not in priority_providers:
            config.disable_provider(provider)
    
    params = config.get_aggregator_params()
    
    return run_aggregator_with_config(
        params, 1000, 'US', 'IN', 'USD', 'INR',
        "Prioritizing Specific Providers"
    )

def scenario_10_singapore_to_india():
    """Scenario 10: Testing Singapore to India corridor."""
    config = AggregatorConfig()
    params = config.get_aggregator_params()
    
    return run_aggregator_with_config(
        params, 1000, 'SG', 'IN', 'SGD', 'INR',
        "Singapore to India Corridor"
    )

def main():
    """Main function to run all scenarios."""
    print_header("RemitScout Aggregator - User Workflow Demonstration")
    
    console.print("This demonstration will show how a typical user would use the RemitScout aggregator "
                 "across various scenarios and use cases.")
    
    # Display all available providers
    config = AggregatorConfig()
    print_section("Available Providers")
    config.print_status()
    
    # Define the scenarios we want to run
    scenarios = [
        scenario_1_basic_comparison,
        scenario_3_lowest_fee,
        scenario_4_different_corridor,
        scenario_5_exclude_problematic_providers,
        scenario_6_maximum_fee
    ]
    
    # Run selected scenarios automatically
    for scenario in scenarios:
        scenario()
        time.sleep(1)  # Pause between scenarios
    
    print_header("RemitScout Aggregator Demo Complete")

if __name__ == "__main__":
    main() 