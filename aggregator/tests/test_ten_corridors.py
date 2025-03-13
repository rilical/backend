#!/usr/bin/env python
"""
Comprehensive corridor test for the RemitScout Aggregator.

This script tests the aggregator across 10 different corridors to evaluate
provider coverage and performance before adding more providers.
"""

import concurrent.futures
import logging
import os
import sys
import time
from decimal import Decimal

from tabulate import tabulate

# Add the parent directory to path to allow imports
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from aggregator.aggregator import Aggregator

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# Define the 10 corridors to test
TEST_CORRIDORS = [
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
        "name": "USD to MXN (US to Mexico)",
        "source_country": "US",
        "dest_country": "MX",
        "source_currency": "USD",
        "dest_currency": "MXN",
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
        "name": "EUR to NGN (Germany to Nigeria)",
        "source_country": "DE",
        "dest_country": "NG",
        "source_currency": "EUR",
        "dest_currency": "NGN",
        "amount": Decimal("1000.00"),
    },
    {
        "name": "AUD to VND (Australia to Vietnam)",
        "source_country": "AU",
        "dest_country": "VN",
        "source_currency": "AUD",
        "dest_currency": "VND",
        "amount": Decimal("1000.00"),
    },
    {
        "name": "CAD to CNY (Canada to China)",
        "source_country": "CA",
        "dest_country": "CN",
        "source_currency": "CAD",
        "dest_currency": "CNY",
        "amount": Decimal("1000.00"),
    },
    {
        "name": "SGD to MYR (Singapore to Malaysia)",
        "source_country": "SG",
        "dest_country": "MY",
        "source_currency": "SGD",
        "dest_currency": "MYR",
        "amount": Decimal("1000.00"),
    },
    {
        "name": "AED to PKR (UAE to Pakistan)",
        "source_country": "AE",
        "dest_country": "PK",
        "source_currency": "AED",
        "dest_currency": "PKR",
        "amount": Decimal("1000.00"),
    },
    {
        "name": "JPY to PHP (Japan to Philippines)",
        "source_country": "JP",
        "dest_country": "PH",
        "source_currency": "JPY",
        "dest_currency": "PHP",
        "amount": Decimal("100000.00"),  # Higher amount for JPY
    },
]


def print_corridor_results(result, corridor_name):
    """Print the results of a corridor test in a readable format."""
    print("\n" + "=" * 80)
    print(f"CORRIDOR: {corridor_name}")
    print("=" * 80)

    # Print parameters
    print(f"Send: {result.get('amount', 'N/A')} {result.get('source_currency')}")
    print(f"From: {result.get('source_country')}")
    print(f"To: {result.get('dest_country')} ({result.get('dest_currency')})")
    print(f"Success: {result['success']}")

    # Calculate provider statistics
    all_providers = result.get("all_providers", [])
    total_providers = len(all_providers)
    success_count = sum(1 for p in all_providers if p.get("success", False))
    fail_count = total_providers - success_count

    print(f"Providers: {total_providers} total, {success_count} successful, {fail_count} failed")

    # Display successful quotes
    if result.get("quotes"):
        print("\nSuccessful Quotes:")
        table_data = []
        for i, quote in enumerate(result.get("quotes", []), 1):
            table_data.append(
                [
                    i,
                    quote.get("provider_id", "Unknown"),
                    quote.get("exchange_rate", "N/A"),
                    quote.get("fee", "N/A"),
                    quote.get("destination_amount", "N/A"),
                    f"{quote.get('delivery_time_minutes', 'N/A')} min"
                    if quote.get("delivery_time_minutes")
                    else "N/A",
                ]
            )

        print(
            tabulate(
                table_data,
                headers=[
                    "#",
                    "Provider",
                    "Rate",
                    "Fee",
                    "Recipient Gets",
                    "Delivery Time",
                ],
                tablefmt="pipe",
                numalign="right",
            )
        )

    # Display failed providers
    failed_providers = [p for p in all_providers if not p.get("success", False)]
    if failed_providers:
        print("\nFailed Providers:")
        table_data = []
        for i, provider in enumerate(failed_providers, 1):
            table_data.append(
                [
                    i,
                    provider.get("provider_id", "Unknown"),
                    provider.get("error_message", "N/A"),
                ]
            )

        print(tabulate(table_data, headers=["#", "Provider", "Error Message"], tablefmt="pipe"))

    return {
        "corridor": corridor_name,
        "success": result["success"],
        "total_providers": total_providers,
        "success_count": success_count,
        "fail_count": fail_count,
        "elapsed": result.get("elapsed_seconds", 0),
    }


def test_corridor(corridor):
    """Test a single corridor and return the results."""
    print(f"Testing: {corridor['name']}")

    # Run the test
    start_time = time.time()
    try:
        result = Aggregator.get_all_quotes(
            source_country=corridor["source_country"],
            dest_country=corridor["dest_country"],
            source_currency=corridor["source_currency"],
            dest_currency=corridor["dest_currency"],
            amount=corridor["amount"],
            sort_by="best_rate",
        )
        elapsed = time.time() - start_time

        print(f"Test completed in {elapsed:.2f} seconds")

        # Print results for this corridor
        summary = print_corridor_results(result, corridor["name"])
        return summary

    except Exception as e:
        elapsed = time.time() - start_time
        logger.exception(f"Error testing corridor {corridor['name']}: {e}")
        print(f"Error: {str(e)}")

        return {
            "corridor": corridor["name"],
            "success": False,
            "total_providers": 0,
            "success_count": 0,
            "fail_count": 0,
            "elapsed": elapsed,
            "error": str(e),
        }


def run_corridor_tests():
    """Run tests for all 10 corridors and summarize results."""
    print("=" * 80)
    print("TESTING 10 REMITTANCE CORRIDORS")
    print("=" * 80)

    # Print which providers we're testing
    provider_names = [p.__class__.__name__ for p in Aggregator.PROVIDERS]
    print(f"Providers: {', '.join(provider_names)}")
    print(f"Testing {len(TEST_CORRIDORS)} corridors")
    print("=" * 80)

    corridor_results = []

    # Test each corridor
    for corridor in TEST_CORRIDORS:
        result = test_corridor(corridor)
        corridor_results.append(result)

    # Print summary table
    print("\n" + "=" * 80)
    print("SUMMARY OF CORRIDOR TESTS")
    print("=" * 80)

    summary_table = []
    for result in corridor_results:
        summary_table.append(
            [
                result["corridor"],
                "Success" if result["success"] else "Failure",
                f"{result['success_count']}/{result['total_providers']}",
                f"{(result['success_count']/result['total_providers']*100) if result['total_providers'] else 0:.1f}%",
                f"{result['elapsed']:.2f}s",
            ]
        )

    print(
        tabulate(
            summary_table,
            headers=["Corridor", "Status", "Providers", "Success Rate", "Time"],
            tablefmt="pipe",
        )
    )

    # Calculate overall stats
    total_tests = len(corridor_results)
    successful_corridors = sum(1 for r in corridor_results if r["success"])
    total_provider_calls = sum(r["total_providers"] for r in corridor_results)
    successful_provider_calls = sum(r["success_count"] for r in corridor_results)

    print("\nOverall Statistics:")
    print(
        f"Corridors: {successful_corridors}/{total_tests} successful ({successful_corridors/total_tests*100:.1f}%)"
    )
    print(
        f"Provider Calls: {successful_provider_calls}/{total_provider_calls} successful ({successful_provider_calls/total_provider_calls*100:.1f}%)"
    )

    # Summarize provider performance across corridors
    provider_success = {}

    for corridor in TEST_CORRIDORS:
        try:
            result = Aggregator.get_all_quotes(
                source_country=corridor["source_country"],
                dest_country=corridor["dest_country"],
                source_currency=corridor["source_currency"],
                dest_currency=corridor["dest_currency"],
                amount=corridor["amount"],
                sort_by="best_rate",
            )

            for provider_result in result.get("all_providers", []):
                provider_id = provider_result.get("provider_id", "Unknown")
                success = provider_result.get("success", False)

                if provider_id not in provider_success:
                    provider_success[provider_id] = {"success": 0, "total": 0}

                provider_success[provider_id]["total"] += 1
                if success:
                    provider_success[provider_id]["success"] += 1

        except Exception:
            continue

    # Print provider performance table
    print("\nProvider Performance:")
    provider_table = []

    for provider_id, stats in provider_success.items():
        success_rate = (stats["success"] / stats["total"] * 100) if stats["total"] > 0 else 0
        provider_table.append(
            [
                provider_id,
                f"{stats['success']}/{stats['total']}",
                f"{success_rate:.1f}%",
            ]
        )

    # Sort by success rate (descending)
    provider_table.sort(key=lambda x: float(x[2].strip("%")), reverse=True)

    print(
        tabulate(
            provider_table,
            headers=["Provider", "Corridors", "Success Rate"],
            tablefmt="pipe",
        )
    )

    print("=" * 80)


if __name__ == "__main__":
    run_corridor_tests()
