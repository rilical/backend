#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RemitScout Aggregator - Output Example
======================================

This script shows a visual representation of what the RemitScout aggregator output 
would look like to a typical user in different scenarios.
"""

import time
import json
from decimal import Decimal
from tabulate import tabulate

def print_banner(text):
    """Print a banner with the given text."""
    print("\n" + "=" * len(text))
    print(text)
    print("=" * len(text) + "\n")

def print_table(data, headers, title=None):
    """Print a formatted table."""
    if title:
        print(f"\n{title}\n" + "-" * len(title))
    print(tabulate(data, headers=headers, tablefmt="grid"))
    print()

def example_basic_comparison():
    """Show what the basic comparison output would look like."""
    print_banner("SCENARIO 1: Basic Comparison - US to India (USD to INR)")
    
    # Simulate the output data
    quotes = [
        {
            "provider_name": "Wise",
            "provider_id": "WiseProvider",
            "exchange_rate": 87.19,
            "fee": 7.33,
            "recipient_gets": 86550.9,
            "delivery_time_minutes": 1440,  # 24 hours
            "payment_method": "DIRECT_DEBIT",
            "success": True
        },
        {
            "provider_name": "RIA",
            "provider_id": "RIAProvider",
            "exchange_rate": 86.65,
            "fee": 6.00,
            "recipient_gets": 87376.6,
            "delivery_time_minutes": 2880,  # 48 hours
            "payment_method": "debitCard",
            "success": True
        },
        {
            "provider_name": "XE",
            "provider_id": "XEAggregatorProvider",
            "exchange_rate": 86.637,
            "fee": 0.00,
            "recipient_gets": 86637.0,
            "delivery_time_minutes": 4320,  # 72 hours
            "payment_method": "BANK_TRANSFER",
            "success": True
        },
        {
            "provider_name": "Remitly",
            "provider_id": "RemitlyProvider",
            "exchange_rate": 85.92,
            "fee": 0.00,
            "recipient_gets": 87320.0,
            "delivery_time_minutes": 1440,  # 24 hours
            "payment_method": "bank",
            "success": True
        },
        {
            "provider_name": "Xoom",
            "provider_id": "XoomProvider",
            "exchange_rate": 83.2,
            "fee": 9.99,
            "recipient_gets": 83200.0,
            "delivery_time_minutes": 1440,  # 24 hours
            "payment_method": "PayPal balance",
            "success": True
        }
    ]
    
    # Format for table display
    table_data = []
    for quote in quotes:
        table_data.append([
            quote["provider_name"],
            f"{float(quote['exchange_rate']):.4f}",
            f"${float(quote['fee']):.2f}",
            f"{float(quote['recipient_gets']):.2f} INR",
            f"{int(quote['delivery_time_minutes']) / 60:.1f} hrs",
            quote.get("payment_method", "N/A")
        ])
    
    print("Sending 1000.00 USD from US to India (INR)")
    print("Sort by: Best Exchange Rate")
    print(f"Execution time: 7.53 seconds")
    print(f"Successfully retrieved quotes from {len(quotes)} providers\n")
    
    print_table(
        table_data,
        headers=["Provider", "Rate", "Fee", "Recipient Gets", "Delivery Time", "Payment Method"]
    )

def example_lowest_fee():
    """Show what the output would look like when sorted by lowest fee."""
    print_banner("SCENARIO 2: Sorting by Lowest Fee - US to India (USD to INR)")
    
    # Simulate the output data - sorted by lowest fee
    quotes = [
        {
            "provider_name": "XE",
            "provider_id": "XEAggregatorProvider",
            "exchange_rate": 86.637,
            "fee": 0.00,
            "recipient_gets": 86637.0,
            "delivery_time_minutes": 4320,  # 72 hours
            "payment_method": "BANK_TRANSFER",
            "success": True
        },
        {
            "provider_name": "Remitly",
            "provider_id": "RemitlyProvider",
            "exchange_rate": 85.92,
            "fee": 0.00,
            "recipient_gets": 87320.0,
            "delivery_time_minutes": 1440,  # 24 hours
            "payment_method": "bank",
            "success": True
        },
        {
            "provider_name": "RIA",
            "provider_id": "RIAProvider",
            "exchange_rate": 86.65,
            "fee": 6.00,
            "recipient_gets": 87376.6,
            "delivery_time_minutes": 2880,  # 48 hours
            "payment_method": "debitCard",
            "success": True
        },
        {
            "provider_name": "Wise",
            "provider_id": "WiseProvider",
            "exchange_rate": 87.19,
            "fee": 7.33,
            "recipient_gets": 86550.9,
            "delivery_time_minutes": 1440,  # 24 hours
            "payment_method": "DIRECT_DEBIT",
            "success": True
        },
        {
            "provider_name": "Xoom",
            "provider_id": "XoomProvider",
            "exchange_rate": 83.2,
            "fee": 9.99,
            "recipient_gets": 83200.0,
            "delivery_time_minutes": 1440,  # 24 hours
            "payment_method": "PayPal balance",
            "success": True
        }
    ]
    
    # Format for table display
    table_data = []
    for quote in quotes:
        table_data.append([
            quote["provider_name"],
            f"{float(quote['exchange_rate']):.4f}",
            f"${float(quote['fee']):.2f}",
            f"{float(quote['recipient_gets']):.2f} INR",
            f"{int(quote['delivery_time_minutes']) / 60:.1f} hrs",
            quote.get("payment_method", "N/A")
        ])
    
    print("Sending 1000.00 USD from US to India (INR)")
    print("Sort by: Lowest Fee")
    print(f"Execution time: 7.42 seconds")
    print(f"Successfully retrieved quotes from {len(quotes)} providers\n")
    
    print_table(
        table_data,
        headers=["Provider", "Rate", "Fee", "Recipient Gets", "Delivery Time", "Payment Method"]
    )

def example_fastest_delivery():
    """Show what the output would look like when sorted by fastest delivery."""
    print_banner("SCENARIO 3: Sorting by Fastest Delivery - US to India (USD to INR)")
    
    # Simulate the output data - sorted by fastest delivery
    quotes = [
        {
            "provider_name": "Wise",
            "provider_id": "WiseProvider",
            "exchange_rate": 87.19,
            "fee": 7.33,
            "recipient_gets": 86550.9,
            "delivery_time_minutes": 1440,  # 24 hours
            "payment_method": "DIRECT_DEBIT",
            "success": True
        },
        {
            "provider_name": "Remitly",
            "provider_id": "RemitlyProvider",
            "exchange_rate": 85.92,
            "fee": 0.00,
            "recipient_gets": 87320.0,
            "delivery_time_minutes": 1440,  # 24 hours
            "payment_method": "bank",
            "success": True
        },
        {
            "provider_name": "Xoom",
            "provider_id": "XoomProvider",
            "exchange_rate": 83.2,
            "fee": 9.99,
            "recipient_gets": 83200.0,
            "delivery_time_minutes": 1440,  # 24 hours
            "payment_method": "PayPal balance",
            "success": True
        },
        {
            "provider_name": "RIA",
            "provider_id": "RIAProvider",
            "exchange_rate": 86.65,
            "fee": 6.00,
            "recipient_gets": 87376.6,
            "delivery_time_minutes": 2880,  # 48 hours
            "payment_method": "debitCard",
            "success": True
        },
        {
            "provider_name": "XE",
            "provider_id": "XEAggregatorProvider",
            "exchange_rate": 86.637,
            "fee": 0.00,
            "recipient_gets": 86637.0,
            "delivery_time_minutes": 4320,  # 72 hours
            "payment_method": "BANK_TRANSFER",
            "success": True
        }
    ]
    
    # Format for table display
    table_data = []
    for quote in quotes:
        table_data.append([
            quote["provider_name"],
            f"{float(quote['exchange_rate']):.4f}",
            f"${float(quote['fee']):.2f}",
            f"{float(quote['recipient_gets']):.2f} INR",
            f"{int(quote['delivery_time_minutes']) / 60:.1f} hrs",
            quote.get("payment_method", "N/A")
        ])
    
    print("Sending 1000.00 USD from US to India (INR)")
    print("Sort by: Fastest Delivery")
    print(f"Execution time: 7.36 seconds")
    print(f"Successfully retrieved quotes from {len(quotes)} providers\n")
    
    print_table(
        table_data,
        headers=["Provider", "Rate", "Fee", "Recipient Gets", "Delivery Time", "Payment Method"]
    )

def example_different_corridor():
    """Show what the output would look like for a different corridor."""
    print_banner("SCENARIO 4: Different Corridor - US to Mexico (USD to MXN)")
    
    # Simulate the output data for US to Mexico
    quotes = [
        {
            "provider_name": "Wise",
            "provider_id": "WiseProvider",
            "exchange_rate": 20.2573,
            "fee": 4.65,
            "recipient_gets": 10034.5,
            "delivery_time_minutes": 1440,  # 24 hours
            "payment_method": "DIRECT_DEBIT",
            "success": True
        },
        {
            "provider_name": "Xoom",
            "provider_id": "XoomProvider",
            "exchange_rate": 20.15,
            "fee": 4.99,
            "recipient_gets": 10075.0,
            "delivery_time_minutes": 1440,  # 24 hours
            "payment_method": "PayPal balance",
            "success": True
        },
        {
            "provider_name": "XE",
            "provider_id": "XEAggregatorProvider",
            "exchange_rate": 20.07,
            "fee": 4.00,
            "recipient_gets": 10035.0,
            "delivery_time_minutes": 4320,  # 72 hours
            "payment_method": "BANK_TRANSFER",
            "success": True
        },
        {
            "provider_name": "RIA",
            "provider_id": "RIAProvider",
            "exchange_rate": 19.99,
            "fee": 1.99,
            "recipient_gets": 10152.0,
            "delivery_time_minutes": 2880,  # 48 hours
            "payment_method": "debitCard",
            "success": True
        },
        {
            "provider_name": "Remitly",
            "provider_id": "RemitlyProvider",
            "exchange_rate": 19.91,
            "fee": 1.99,
            "recipient_gets": 10125.0,
            "delivery_time_minutes": 1440,  # 24 hours
            "payment_method": "bank",
            "success": True
        }
    ]
    
    # Format for table display
    table_data = []
    for quote in quotes:
        table_data.append([
            quote["provider_name"],
            f"{float(quote['exchange_rate']):.4f}",
            f"${float(quote['fee']):.2f}",
            f"{float(quote['recipient_gets']):.2f} MXN",
            f"{int(quote['delivery_time_minutes']) / 60:.1f} hrs",
            quote.get("payment_method", "N/A")
        ])
    
    print("Sending 500.00 USD from US to Mexico (MXN)")
    print("Sort by: Best Exchange Rate")
    print(f"Execution time: 7.57 seconds")
    print(f"Successfully retrieved quotes from {len(quotes)} providers\n")
    
    print_table(
        table_data,
        headers=["Provider", "Rate", "Fee", "Recipient Gets", "Delivery Time", "Payment Method"]
    )

def example_filtered_max_fee():
    """Show what the output would look like with a maximum fee filter."""
    print_banner("SCENARIO 5: Maximum Fee Filter - US to India (USD to INR)")
    
    # Simulate the output data with max fee of $5.00
    quotes = [
        {
            "provider_name": "XE",
            "provider_id": "XEAggregatorProvider",
            "exchange_rate": 86.637,
            "fee": 0.00,
            "recipient_gets": 86637.0,
            "delivery_time_minutes": 4320,  # 72 hours
            "payment_method": "BANK_TRANSFER",
            "success": True
        },
        {
            "provider_name": "Remitly",
            "provider_id": "RemitlyProvider",
            "exchange_rate": 85.92,
            "fee": 0.00,
            "recipient_gets": 87320.0,
            "delivery_time_minutes": 1440,  # 24 hours
            "payment_method": "bank",
            "success": True
        },
        {
            "provider_name": "RIA",
            "provider_id": "RIAProvider",
            "exchange_rate": 86.65,
            "fee": 5.00,  # Adjusted to be within filter
            "recipient_gets": 87376.6,
            "delivery_time_minutes": 2880,  # 48 hours
            "payment_method": "debitCard",
            "success": True
        }
    ]
    
    # Format for table display
    table_data = []
    for quote in quotes:
        table_data.append([
            quote["provider_name"],
            f"{float(quote['exchange_rate']):.4f}",
            f"${float(quote['fee']):.2f}",
            f"{float(quote['recipient_gets']):.2f} INR",
            f"{int(quote['delivery_time_minutes']) / 60:.1f} hrs",
            quote.get("payment_method", "N/A")
        ])
    
    print("Sending 1000.00 USD from US to India (INR)")
    print("Sort by: Best Exchange Rate")
    print("Filter applied: Maximum Fee = $5.00")
    print(f"Execution time: 7.48 seconds")
    print(f"Successfully retrieved quotes from {len(quotes)} providers (after filtering)\n")
    
    print_table(
        table_data,
        headers=["Provider", "Rate", "Fee", "Recipient Gets", "Delivery Time", "Payment Method"]
    )

def example_command_line():
    """Show a CLI output example."""
    print_banner("CLI EXAMPLE: US to India (USD to INR)")
    
    cli_output = """$ python3 apps/cli.py --amount 1000 --from-country US --to-country IN --from-currency USD --to-currency INR --sort-by best_rate --exclude-providers PangeaProvider,MukuruProvider --max-fee 8

+------------+--------+-------+------------------+--------------------+------------------+
| Provider   |   Rate |   Fee |   Recipient Gets |   Delivery (hours) | Payment Method   |
+============+========+=======+==================+====================+==================+
| wise       | 87.19  |  7.33 |          86550.9 |                 24 | DIRECT_DEBIT     |
+------------+--------+-------+------------------+--------------------+------------------+
| ria        | 86.65  |  6.00 |          87376.6 |                 48 | debitCard        |
+------------+--------+-------+------------------+--------------------+------------------+
| XE         | 86.64  |  0.00 |          86637.0 |                 72 | BANK_TRANSFER    |
+------------+--------+-------+------------------+--------------------+------------------+
| remitly    | 85.92  |  0.00 |          87320.0 |                 24 | bank             |
+------------+--------+-------+------------------+--------------------+------------------+

Total quotes: 4
Execution time: 7.65 seconds
Filters Applied:
  sort_by: best_rate
  max_delivery_time_minutes: None
  max_fee: 8.0
  custom_filter: False"""
    
    print(cli_output)

def main():
    """Run all example outputs."""
    print_banner("REMITSCOUT AGGREGATOR - EXAMPLE OUTPUTS")
    
    print("This script demonstrates what the RemitScout aggregator output would look like to a typical user.")
    print("Below are examples of different scenarios and sorting options.\n")
    
    example_basic_comparison()
    example_lowest_fee()
    example_fastest_delivery()
    example_different_corridor()
    example_filtered_max_fee()
    example_command_line()
    
    print_banner("END OF EXAMPLES")

if __name__ == "__main__":
    main() 