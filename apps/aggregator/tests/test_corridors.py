#!/usr/bin/env python
"""
Test script for the Aggregator class.

This script tests the Aggregator with 10 different currency corridors
to evaluate which providers support which corridors and how they compare.
"""

import json
import logging
import os
import sys
import time
from decimal import Decimal
from typing import Any, Dict, List

from tabulate import tabulate

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("aggregator_test")

# Import the Aggregator class
from apps.aggregator.aggregator import Aggregator

# Define the corridors to test
CORRIDORS = [
    {
        "name": "USD to INR (US to India)",
        "source_country": "US",
        "dest_country": "IN",
        "source_currency": "USD",
        "dest_currency": "INR",
        "amount": Decimal("1000.00"),
    },
    {
        "name": "USD to PHP (US to Philippines)",
        "source_country": "US",
        "dest_country": "PH",
        "source_currency": "USD",
        "dest_currency": "PHP",
        "amount": Decimal("1000.00"),
    },
    {
        "name": "GBP to INR (UK to India)",
        "source_country": "GB",
        "dest_country": "IN",
        "source_currency": "GBP",
        "dest_currency": "INR",
        "amount": Decimal("1000.00"),
    },
    {
        "name": "EUR to NGN (Europe to Nigeria)",
        "source_country": "DE",  # Using Germany as a representative EU country
        "dest_country": "NG",
        "source_currency": "EUR",
        "dest_currency": "NGN",
        "amount": Decimal("1000.00"),
    },
    {
        "name": "CAD to INR (Canada to India)",
        "source_country": "CA",
        "dest_country": "IN",
        "source_currency": "CAD",
        "dest_currency": "INR",
        "amount": Decimal("1000.00"),
    },
    {
        "name": "AUD to INR (Australia to India)",
        "source_country": "AU",
        "dest_country": "IN",
        "source_currency": "AUD",
        "dest_currency": "INR",
        "amount": Decimal("1000.00"),
    },
    {
        "name": "SGD to INR (Singapore to India)",
        "source_country": "SG",
        "dest_country": "IN",
        "source_currency": "SGD",
        "dest_currency": "INR",
        "amount": Decimal("1000.00"),
    },
    {
        "name": "USD to MXN (US to Mexico)",
        "source_country": "US",
        "dest_country": "MX",
        "source_currency": "USD",
        "dest_currency": "MXN",
        "amount": Decimal("1000.00"),
    },
    {
        "name": "GBP to EUR (UK to Europe)",
        "source_country": "GB",
        "dest_country": "DE",  # Using Germany as a representative EU country
        "source_currency": "GBP",
        "dest_currency": "EUR",
        "amount": Decimal("1000.00"),
    },
    {
        "name": "AUD to PHP (Australia to Philippines)",
        "source_country": "AU",
        "dest_country": "PH",
        "source_currency": "AUD",
        "dest_currency": "PHP",
        "amount": Decimal("1000.00"),
    },
]


def run_aggregator_test(corridor: Dict[str, Any], max_workers: int = 5) -> Dict[str, Any]:
    """
    Run the aggregator for a specific corridor.

    Args:
        corridor: Dictionary containing corridor parameters
        max_workers: Number of concurrent workers to use

    Returns:
        The results from the aggregator
    """
    logger.info(f"Testing corridor: {corridor['name']}")

    start_time = time.time()

    result = Aggregator.get_all_quotes(
        source_country=corridor["source_country"],
        dest_country=corridor["dest_country"],
        source_currency=corridor["source_currency"],
        dest_currency=corridor["dest_currency"],
        amount=corridor["amount"],
        sort_by="best_rate",
        max_workers=max_workers,
    )

    end_time = time.time()
    result["test_duration"] = end_time - start_time

    return result


def print_corridor_summary(corridor: Dict[str, Any], result: Dict[str, Any]) -> None:
    """
    Print a summary of results for a corridor.

    Args:
        corridor: Dictionary containing corridor parameters
        result: The results from the aggregator
    """
    print("\n" + "=" * 80)
    print(f"CORRIDOR: {corridor['name']}")
    print(
        f"Send: {corridor['amount']} {corridor['source_currency']} from {corridor['source_country']} "
        f"to {corridor['dest_country']} in {corridor['dest_currency']}"
    )
    print(f"Test Duration: {result['test_duration']:.2f} seconds")

    success_count = sum(1 for quote in result["results"] if quote.get("success"))
    fail_count = len(result["results"]) - success_count

    print(f"Overall Success: {result['success']}")
    print(
        f"Providers: {len(result['results'])} total, {success_count} successful, {fail_count} failed"
    )

    if success_count > 0:
        # Prepare data for tabulation
        table_data = []
        for quote in result["results"]:
            if quote.get("success"):
                table_data.append(
                    [
                        quote.get("provider_id", "Unknown"),
                        f"{quote.get('exchange_rate', 0):.4f}",
                        f"{quote.get('fee', 0):.2f} {corridor['source_currency']}",
                        f"{quote.get('destination_amount', 0):.2f} {corridor['dest_currency']}",
                        f"{quote.get('delivery_time_minutes', 'N/A')} min",
                    ]
                )

        # Print table with results
        headers = ["Provider", "Rate", "Fee", "Recipient Gets", "Delivery Time"]
        print("\nSuccessful Quotes:")
        print(tabulate(table_data, headers=headers, tablefmt="pipe"))

    # Print failed providers
    failed_providers = [
        quote.get("provider_id", "Unknown")
        for quote in result["results"]
        if not quote.get("success")
    ]
    if failed_providers:
        print("\nFailed Providers:", ", ".join(failed_providers))

    print("=" * 80)


def save_results_to_file(all_results: List[Dict[str, Any]], filename: str) -> None:
    """
    Save all test results to a JSON file.

    Args:
        all_results: List of all test results
        filename: Name of the file to save results to
    """

    # Convert Decimal values to float for JSON serialization
    def decimal_to_float(obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return obj

    with open(filename, "w") as f:
        json.dump(all_results, f, default=decimal_to_float, indent=2)

    print(f"Results saved to {filename}")


def main():
    """Run tests for all corridors and print results."""
    all_results = []

    print("\nAGGREGATOR CORRIDOR TESTS")
    print("=========================\n")
    print(f"Testing {len(CORRIDORS)} corridors with all available providers")

    for corridor in CORRIDORS:
        result = run_aggregator_test(corridor)
        print_corridor_summary(corridor, result)

        # Store the results
        all_results.append({"corridor": corridor, "result": result})

    # Save all results to a file for later analysis
    save_results_to_file(all_results, "aggregator_test_results.json")

    # Print a final summary
    print("\nTEST SUMMARY")
    print("===========")

    table_data = []
    for i, test in enumerate(all_results, 1):
        corridor = test["corridor"]
        result = test["result"]
        success_count = sum(1 for quote in result["results"] if quote.get("success"))

        table_data.append(
            [
                i,
                corridor["name"],
                f"{success_count}/{len(result['results'])}",
                f"{result['test_duration']:.2f}s",
            ]
        )

    headers = ["#", "Corridor", "Success Ratio", "Duration"]
    print(tabulate(table_data, headers=headers, tablefmt="pipe"))


if __name__ == "__main__":
    main()
