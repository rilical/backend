#!/usr/bin/env python
"""
A minimal test script for the aggregator concept.

This script defines a simplified Aggregator class with only a few providers
to test the core functionality without dealing with import issues.
"""

import concurrent.futures
import logging
import os
import sys
import time
from decimal import Decimal
from typing import Any, Dict, List, Optional

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("aggregator_test")

# Import a few provider classes that are likely to work
try:
    from apps.providers.wise.integration import WiseProvider
    from apps.providers.xe.integration import XEProvider

    PROVIDERS = [WiseProvider(), XEProvider()]
    logger.info("Imported Wise and XE providers")
except ImportError as e:
    logger.error(f"Error importing providers: {e}")
    # Provide dummy providers for testing
    PROVIDERS = []
    logger.info("Using empty provider list due to import errors")


class SimpleAggregator:
    """
    A simplified version of the Aggregator for testing.
    """

    PROVIDERS = PROVIDERS

    @classmethod
    def get_all_quotes(
        cls,
        source_country: str,
        dest_country: str,
        source_currency: str,
        dest_currency: str,
        amount: Decimal,
        max_workers: int = 5,
    ) -> Dict[str, Any]:
        """
        Minimal implementation of get_all_quotes that just calls providers in parallel.
        """
        logger.info(
            f"Testing corridor: {source_country}->{dest_country}, {source_currency}->{dest_currency}"
        )

        start_time = time.time()

        # We'll store final results in a list
        results = []

        # Function to call a provider and handle exceptions
        def call_provider(provider):
            provider_name = getattr(provider, "name", provider.__class__.__name__)
            logger.info(f"Calling provider {provider_name}")
            try:
                # Try to call get_quote or get_exchange_rate
                if hasattr(provider, "get_quote"):
                    resp = provider.get_quote(
                        amount=amount,
                        source_currency=source_currency,
                        dest_currency=dest_currency,
                        source_country=source_country,
                        dest_country=dest_country,
                    )
                else:
                    resp = provider.get_exchange_rate(
                        send_amount=amount,
                        send_currency=source_currency,
                        target_currency=dest_currency,
                        send_country=source_country,
                        receive_country=dest_country,
                    )

                # Add provider_id if it's missing
                if not resp.get("provider_id"):
                    resp["provider_id"] = provider_name

                return resp
            except Exception as exc:
                # Catch any exception, return a fail record
                logger.exception(f"Provider {provider_name} threw exception: {exc}")
                return {
                    "provider_id": provider_name,
                    "success": False,
                    "error_message": str(exc),
                }

        # Launch provider calls in parallel if we have multiple providers
        if len(cls.PROVIDERS) > 1:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_provider = {executor.submit(call_provider, p): p for p in cls.PROVIDERS}

                for future in concurrent.futures.as_completed(future_to_provider):
                    result = future.result()
                    results.append(result)
        elif len(cls.PROVIDERS) == 1:
            # Just call the single provider directly
            results.append(call_provider(cls.PROVIDERS[0]))
        else:
            # No providers available
            logger.warning("No providers available for testing")

        # Aggregator is successful if at least one provider succeeded
        aggregator_success = any(r.get("success") for r in results)

        # Build final response
        aggregator_response = {
            "success": aggregator_success,
            "source_country": source_country,
            "dest_country": dest_country,
            "source_currency": source_currency,
            "dest_currency": dest_currency,
            "send_amount": float(amount),
            "results": results,
            "timestamp": time.time(),
        }

        end_time = time.time()
        logger.info(
            f"Aggregator finished in {end_time - start_time:.2f}s; success={aggregator_success}"
        )
        return aggregator_response


def main():
    """Run a simple test of the aggregator."""
    print("\nTESTING SIMPLE AGGREGATOR")
    print("=========================\n")

    # If we have no providers, add a dummy one for testing
    if not SimpleAggregator.PROVIDERS:

        class DummyProvider:
            name = "DummyProvider"

            def get_quote(self, **kwargs):
                return {
                    "success": True,
                    "provider_id": "DummyProvider",
                    "exchange_rate": 83.5,
                    "fee": 5.0,
                    "send_amount": 1000.0,
                    "destination_amount": 83500.0,
                    "delivery_time_minutes": 60,
                }

        SimpleAggregator.PROVIDERS = [DummyProvider()]
        print("Using dummy provider for testing\n")

    # Test with USD to INR corridor
    result = SimpleAggregator.get_all_quotes(
        source_country="US",
        dest_country="IN",
        source_currency="USD",
        dest_currency="INR",
        amount=Decimal("1000.00"),
    )

    # Print the results
    print("\nQUOTE RESULTS:")
    print(f"Success: {result['success']}")
    print(f"Providers tested: {len(result['results'])}")

    for quote in result["results"]:
        print(f"\nProvider: {quote.get('provider_id', 'Unknown')}")
        print(f"Success: {quote.get('success', False)}")

        if quote.get("success"):
            print(f"Exchange Rate: {quote.get('exchange_rate', 'N/A')}")
            print(f"Fee: {quote.get('fee', 'N/A')} {result['source_currency']}")
            print(
                f"Recipient Gets: {quote.get('destination_amount', 'N/A')} {result['dest_currency']}"
            )
            print(f"Delivery Time: {quote.get('delivery_time_minutes', 'N/A')} minutes")
        else:
            print(f"Error: {quote.get('error_message', 'Unknown error')}")


if __name__ == "__main__":
    main()
