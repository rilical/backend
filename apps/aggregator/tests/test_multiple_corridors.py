#!/usr/bin/env python3
"""
Test script to verify the aggregator functionality across multiple corridors.
This helps ensure the aggregator works reliably for different country/currency combinations.
"""

import json
import logging
import os
import sys
import time
from decimal import Decimal
from typing import Any, Dict, List, Tuple

from tabulate import tabulate

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

# Configure basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# Import the aggregator
from apps.aggregator.aggregator import Aggregator

# Define test corridors
TEST_CORRIDORS = [
    # source_country, dest_country, source_currency, dest_currency, amount
    ("US", "IN", "USD", "INR", Decimal("1000.00")),
    ("US", "PH", "USD", "PHP", Decimal("500.00")),
    ("US", "MX", "USD", "MXN", Decimal("300.00")),
    ("GB", "IN", "GBP", "INR", Decimal("500.00")),
    ("CA", "IN", "CAD", "INR", Decimal("1000.00")),
]

# Define sorting methods to test
SORTING_METHODS = ["best_rate", "lowest_fee", "fastest_time"]


def run_corridor_test(
    corridor: Tuple[str, str, str, str, Decimal], sort_by: str = "best_rate"
) -> Dict[str, Any]:
    """
    Run the aggregator test for a specific corridor.

    Args:
        corridor: Tuple containing (source_country, dest_country, source_currency, dest_currency, amount)
        sort_by: Sorting method to use

    Returns:
        Dict containing test results
    """
    source_country, dest_country, source_currency, dest_currency, amount = corridor

    logger.info(
        f"Testing corridor: {source_country} → {dest_country} ({source_currency} → {dest_currency}) for {amount}, sort by: {sort_by}"
    )

    start_time = time.time()

    result = Aggregator.get_all_quotes(
        source_country=source_country,
        dest_country=dest_country,
        source_currency=source_currency,
        dest_currency=dest_currency,
        amount=amount,
        sort_by=sort_by,
    )

    end_time = time.time()
    execution_time = end_time - start_time

    # Count total providers and successful providers
    total_providers = len(Aggregator.PROVIDERS)

    # Handle different result formats
    success_count = 0

    if isinstance(result.get("quotes", {}), dict):
        success_count = len(result["quotes"])
    elif isinstance(result.get("quotes", []), list):
        success_count = len(result.get("quotes", []))

    return {
        "corridor": corridor,
        "sort_by": sort_by,
        "execution_time": execution_time,
        "success_count": success_count,
        "total_providers": total_providers,
        "result": result,
    }


def print_test_results(test_results: Dict[str, Any]) -> None:
    """
    Print formatted test results.

    Args:
        test_results: Dictionary containing test results
    """
    corridor = test_results["corridor"]
    source_country, dest_country, source_currency, dest_currency, amount = corridor

    print(
        f"\n=== Corridor Test Results: {source_country} → {dest_country} ({source_currency} → {dest_currency}) ==="
    )
    print(f"Amount: {amount} {source_currency}")
    print(f"Sort by: {test_results['sort_by']}")
    print(f"Time taken: {test_results['execution_time']:.2f} seconds")
    print(f"Success: {test_results['success_count']}/{test_results['total_providers']} providers")

    # Format results for tabulation
    headers = [
        "Provider",
        "Status",
        "Rate",
        "Fee",
        "Recipient Gets",
        "Delivery Time (min)",
        "Error Message",
    ]
    rows = []

    result = test_results["result"]

    # Add successful providers to the table
    quotes = result.get("quotes", {})
    if isinstance(quotes, dict):
        for provider_id, quote in quotes.items():
            rows.append(
                [
                    provider_id,
                    "Success",
                    quote.get("exchange_rate", "N/A"),
                    quote.get("fee", "N/A"),
                    quote.get("destination_amount", "N/A"),
                    quote.get("delivery_time_minutes", "N/A"),
                    "N/A",
                ]
            )
    elif isinstance(quotes, list):
        for quote in quotes:
            rows.append(
                [
                    quote.get("provider_id", "Unknown"),
                    "Success",
                    quote.get("exchange_rate", "N/A"),
                    quote.get("fee", "N/A"),
                    quote.get("destination_amount", "N/A"),
                    quote.get("delivery_time_minutes", "N/A"),
                    "N/A",
                ]
            )

    # Add failed providers to the table if any
    errors = result.get("errors", {})
    if isinstance(errors, dict):
        for provider_id, error in errors.items():
            rows.append(
                [
                    provider_id,
                    "Failure",
                    "N/A",
                    "N/A",
                    "N/A",
                    "N/A",
                    error.get("error_message", "Unknown error"),
                ]
            )
    elif isinstance(errors, list):
        for error in errors:
            rows.append(
                [
                    error.get("provider_id", "Unknown"),
                    "Failure",
                    "N/A",
                    "N/A",
                    "N/A",
                    "N/A",
                    error.get("error_message", "Unknown error"),
                ]
            )

    print("\nDetailed Results:")
    print(tabulate(rows, headers=headers, tablefmt="pretty"))


def run_comprehensive_test():
    """Run tests for all defined corridors and sorting methods."""
    total_tests = len(TEST_CORRIDORS) * len(SORTING_METHODS)
    successful_tests = 0
    failed_tests = 0

    corridor_results = {}

    print(f"=== Starting Comprehensive Corridor Tests ===")
    print(f"Testing {len(TEST_CORRIDORS)} corridors with {len(SORTING_METHODS)} sorting methods")

    for corridor in TEST_CORRIDORS:
        source_country, dest_country, source_currency, dest_currency, amount = corridor
        corridor_key = f"{source_country}-{dest_country}-{source_currency}-{dest_currency}"
        corridor_results[corridor_key] = {
            "success": 0,
            "total": len(SORTING_METHODS),
            "tests": [],
        }

        for sort_by in SORTING_METHODS:
            try:
                test_result = run_corridor_test(corridor, sort_by)
                print_test_results(test_result)

                # Track success based on whether any provider quotes were returned
                if test_result["success_count"] > 0:
                    successful_tests += 1
                    corridor_results[corridor_key]["success"] += 1
                else:
                    failed_tests += 1

                corridor_results[corridor_key]["tests"].append(
                    {
                        "sort_by": sort_by,
                        "providers_succeeded": test_result["success_count"],
                        "execution_time": test_result["execution_time"],
                    }
                )

            except Exception as e:
                logger.exception(
                    f"Error testing corridor {corridor_key} with sort_by={sort_by}: {e}"
                )
                failed_tests += 1

    # Print summary
    print("\n=== Comprehensive Test Summary ===")
    print(f"Total tests: {total_tests}")
    print(f"Successful tests: {successful_tests}")
    print(f"Failed tests: {failed_tests}")
    print(f"Success rate: {(successful_tests / total_tests) * 100:.2f}%")

    # Print corridor-specific results
    print("\n=== Corridor Success Rates ===")
    corridor_headers = [
        "Corridor",
        "Success Rate",
        "Avg Providers",
        "Avg Execution Time",
    ]
    corridor_rows = []

    for corridor_key, result in corridor_results.items():
        success_rate = (result["success"] / result["total"]) * 100
        avg_providers = (
            sum(test["providers_succeeded"] for test in result["tests"]) / len(result["tests"])
            if result["tests"]
            else 0
        )
        avg_execution_time = (
            sum(test["execution_time"] for test in result["tests"]) / len(result["tests"])
            if result["tests"]
            else 0
        )

        corridor_rows.append(
            [
                corridor_key,
                f"{success_rate:.2f}%",
                f"{avg_providers:.1f}",
                f"{avg_execution_time:.2f}s",
            ]
        )

    print(tabulate(corridor_rows, headers=corridor_headers, tablefmt="pretty"))

    return successful_tests == total_tests


if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)
