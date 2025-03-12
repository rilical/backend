#!/usr/bin/env python3
"""
Test script to specifically verify the XoomProvider integration with the aggregator.
"""

import json
import logging
import os
import sys
import time
from decimal import Decimal

from tabulate import tabulate

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

# Configure basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# Import the aggregator and provider
from apps.aggregator.aggregator import Aggregator
from apps.providers.xoom.integration import XoomProvider


def run_xoom_test():
    """Test the XoomProvider through the aggregator."""

    # Define test parameters
    source_country = "US"
    dest_country = "IN"
    source_currency = "USD"
    dest_currency = "INR"
    amount = Decimal("1000.00")

    logger.info(
        f"Testing XoomProvider with {source_country} → {dest_country} ({source_currency} → {dest_currency}) for {amount}"
    )

    # Test with only XoomProvider
    start_time = time.time()

    result = Aggregator.get_all_quotes(
        source_country=source_country,
        dest_country=dest_country,
        source_currency=source_currency,
        dest_currency=dest_currency,
        amount=amount,
        sort_by="best_rate",
        exclude_providers=[
            p.__class__.__name__ for p in Aggregator.PROVIDERS if not isinstance(p, XoomProvider)
        ],
    )

    end_time = time.time()
    execution_time = end_time - start_time

    # Log the result for debugging
    logger.info(f"Aggregator result: {json.dumps(result, default=str)}")

    # Count successful and failed providers
    success_count = len(result.get("quotes", {}))
    total_providers = 1  # Since we're only testing XoomProvider

    # Display results in a table format
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

    # Handle different result formats for quotes
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

    print(f"\n=== XoomProvider Test Results ===")
    print(f"Corridor: {source_country} → {dest_country} ({source_currency} → {dest_currency})")
    print(f"Amount: {amount} {source_currency}")
    print(f"Time taken: {execution_time:.2f} seconds")
    print(f"Success: {success_count}/{total_providers} providers")
    print(f"\nDetailed Results:")
    print(tabulate(rows, headers=headers, tablefmt="pretty"))

    return success_count == total_providers


if __name__ == "__main__":
    success = run_xoom_test()
    sys.exit(0 if success else 1)
