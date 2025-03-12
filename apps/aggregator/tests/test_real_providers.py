#!/usr/bin/env python
"""
Test script for real provider integrations.

This script tests each provider individually with real API calls,
gradually building up to testing multiple providers together.
"""

import concurrent.futures
import logging
import os
import sys
import time
from decimal import Decimal
from typing import Any, Dict, List, Optional

from tabulate import tabulate

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("aggregator_test")

# Test parameters
TEST_CORRIDOR = {
    "name": "USD to INR (US to India)",
    "source_country": "US",
    "dest_country": "IN",
    "source_currency": "USD",
    "dest_currency": "INR",
    "amount": Decimal("1000.00"),
}

# Provider-specific parameter mappings
PROVIDER_PARAMS = {
    "XEAggregatorProvider": {
        "get_quote": {
            "amount": "amount",
            "source_currency": "source_currency",
            "target_country": "dest_country",
            # XE doesn't use dest_currency, it determines it from target_country
        },
        "get_exchange_rate": {
            "send_amount": "amount",
            "send_currency": "source_currency",
            "receive_country": "dest_country",
        },
    },
    "WiseProvider": {
        "get_quote": {
            "amount": "amount",
            "source_currency": "source_currency",
            "target_currency": "dest_currency",
            "source_country": "source_country",
            "target_country": "dest_country",
        }
    },
    "RIAProvider": {
        "get_quote": {
            "amount": "amount",
            "source_currency": "source_currency",
            "dest_currency": "dest_currency",
            "source_country": "source_country",
            "dest_country": "dest_country",
            "payment_method": "debitCard",  # Default payment method
            "delivery_method": "bankDeposit",  # Default delivery method
        }
    },
    "TransferGoProvider": {
        "get_quote": {
            "amount": "amount",
            "source_currency": "source_currency",
            "destination_currency": "dest_currency",
            "source_country": "source_country",
            "destination_country": "dest_country",
        }
    },
}


def test_provider(provider_class, provider_args=None, **corridor_params):
    """
    Test a single provider with the given corridor parameters.

    Args:
        provider_class: The provider class to test
        provider_args: Optional args to pass to the provider constructor
        **corridor_params: Corridor parameters

    Returns:
        The provider result
    """
    if provider_args is None:
        provider_args = {}

    # Use test corridor params if not specified
    for key, value in TEST_CORRIDOR.items():
        if key not in corridor_params and key not in ("name"):
            corridor_params[key] = value

    try:
        # Initialize the provider
        provider_name = provider_class.__name__
        logger.info(f"Testing provider: {provider_name}")

        provider = provider_class(**provider_args)

        # Check if we have provider-specific parameter mappings
        provider_specific_params = PROVIDER_PARAMS.get(provider_name, {})

        # Determine the method to call (get_quote or get_exchange_rate)
        if hasattr(provider, "get_quote"):
            logger.info(f"Calling {provider_name}.get_quote()")

            # Use provider-specific parameters if available
            if "get_quote" in provider_specific_params:
                param_mapping = provider_specific_params["get_quote"]
                kwargs = {}

                for target_param, source_param in param_mapping.items():
                    if isinstance(source_param, str) and source_param in corridor_params:
                        kwargs[target_param] = corridor_params[source_param]
                    else:
                        # For hardcoded values
                        kwargs[target_param] = source_param

                logger.info(f"Using provider-specific parameters: {kwargs}")
                result = provider.get_quote(**kwargs)
            else:
                # Use standard parameters
                try:
                    result = provider.get_quote(
                        amount=corridor_params["amount"],
                        source_currency=corridor_params["source_currency"],
                        dest_currency=corridor_params["dest_currency"],
                        source_country=corridor_params["source_country"],
                        dest_country=corridor_params["dest_country"],
                    )
                except TypeError as e:
                    # Try alternate parameter names
                    logger.warning(f"TypeError with standard parameters: {e}")
                    logger.info(f"Trying alternate parameter names...")

                    result = provider.get_quote(
                        amount=corridor_params["amount"],
                        source_currency=corridor_params["source_currency"],
                        destination_currency=corridor_params["dest_currency"],
                        source_country=corridor_params["source_country"],
                        destination_country=corridor_params["dest_country"],
                    )
        else:
            logger.info(f"Calling {provider_name}.get_exchange_rate()")

            # Use provider-specific parameters if available
            if "get_exchange_rate" in provider_specific_params:
                param_mapping = provider_specific_params["get_exchange_rate"]
                kwargs = {}

                for target_param, source_param in param_mapping.items():
                    if isinstance(source_param, str) and source_param in corridor_params:
                        kwargs[target_param] = corridor_params[source_param]
                    else:
                        # For hardcoded values
                        kwargs[target_param] = source_param

                logger.info(f"Using provider-specific parameters: {kwargs}")
                result = provider.get_exchange_rate(**kwargs)
            else:
                # Use standard parameters
                try:
                    result = provider.get_exchange_rate(
                        send_amount=corridor_params["amount"],
                        send_currency=corridor_params["source_currency"],
                        target_currency=corridor_params["dest_currency"],
                        send_country=corridor_params["source_country"],
                        receive_country=corridor_params["dest_country"],
                    )
                except TypeError as e:
                    # Try alternate parameter names
                    logger.warning(f"TypeError with standard parameters: {e}")
                    logger.info(f"Trying alternate parameter names...")

                    result = provider.get_exchange_rate(
                        send_amount=corridor_params["amount"],
                        source_currency=corridor_params["source_currency"],
                        destination_currency=corridor_params["dest_currency"],
                        source_country=corridor_params["source_country"],
                        destination_country=corridor_params["dest_country"],
                    )

        # Add provider_id if missing
        if not result.get("provider_id"):
            result["provider_id"] = provider_name

        # Print result
        if result.get("success"):
            logger.info(f"SUCCESS: {provider_name} returned a quote")
            print(f"\n{provider_name} SUCCESS:")
            print(f"Exchange Rate: {result.get('exchange_rate', 'N/A')}")
            print(f"Fee: {result.get('fee', 'N/A')} {corridor_params['source_currency']}")
            print(
                f"Recipient Gets: {result.get('destination_amount', 'N/A')} {corridor_params['dest_currency']}"
            )
            print(f"Delivery Time: {result.get('delivery_time_minutes', 'N/A')} minutes\n")
        else:
            logger.warning(
                f"FAILED: {provider_name} returned error: {result.get('error_message', 'Unknown error')}"
            )
            print(f"\n{provider_name} FAILED:")
            print(f"Error: {result.get('error_message', 'Unknown error')}\n")

        return result

    except Exception as e:
        logger.error(f"Error testing provider {provider_class.__name__}: {str(e)}", exc_info=True)
        return {
            "success": False,
            "provider_id": provider_class.__name__,
            "error_message": str(e),
        }


def test_multiple_providers(provider_classes, **corridor_params):
    """
    Test multiple providers in parallel.

    Args:
        provider_classes: List of provider classes to test
        **corridor_params: Corridor parameters

    Returns:
        List of provider results
    """
    # Use test corridor params if not specified
    for key, value in TEST_CORRIDOR.items():
        if key not in corridor_params and key not in ("name"):
            corridor_params[key] = value

    results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(provider_classes)) as executor:
        future_to_provider = {
            executor.submit(test_provider, provider_class, {}, **corridor_params): provider_class
            for provider_class in provider_classes
        }

        for future in concurrent.futures.as_completed(future_to_provider):
            result = future.result()
            results.append(result)

    return results


def print_test_summary(results):
    """
    Print a summary of test results.

    Args:
        results: List of provider results
    """
    success_count = sum(1 for r in results if r.get("success"))
    fail_count = len(results) - success_count

    print(f"\nTEST SUMMARY")
    print(f"===========")
    print(f"Total Providers: {len(results)}")
    print(f"Successful: {success_count}")
    print(f"Failed: {fail_count}")

    if results:
        # Create table for display
        table_data = []
        for result in results:
            provider_id = result.get("provider_id", "Unknown")
            success = result.get("success", False)

            if success:
                rate = result.get("exchange_rate", "N/A")
                fee = result.get("fee", "N/A")
                table_data.append(
                    [
                        provider_id,
                        "✓" if success else "✗",
                        rate,
                        fee,
                        result.get("delivery_time_minutes", "N/A"),
                    ]
                )
            else:
                error = result.get("error_message", "Unknown error")
                table_data.append(
                    [
                        provider_id,
                        "✗",
                        "N/A",
                        "N/A",
                        error[:50] + "..." if len(error) > 50 else error,
                    ]
                )

        headers = ["Provider", "Success", "Rate", "Fee", "Delivery Time/Error"]
        print("\n" + tabulate(table_data, headers=headers, tablefmt="pipe"))


def main():
    """
    Run the tests for individual providers and groups of providers.
    """
    print("\nTESTING REAL PROVIDERS")
    print("=====================\n")

    all_results = []

    # Try XE with its specific parameter requirements
    try:
        from apps.providers.xe.integration import XEAggregatorProvider

        print("\n=== Testing XEAggregatorProvider ===")
        result = test_provider(XEAggregatorProvider)
        all_results.append(result)
    except ImportError as e:
        logger.error(f"Could not import XEAggregatorProvider: {e}")

    try:
        from apps.providers.wise.integration import WiseProvider

        print("\n=== Testing WiseProvider ===")
        result = test_provider(WiseProvider)
        all_results.append(result)
    except ImportError as e:
        logger.error(f"Could not import WiseProvider: {e}")

    try:
        from apps.providers.remitly.integration import RemitlyProvider

        print("\n=== Testing RemitlyProvider ===")
        result = test_provider(RemitlyProvider)
        all_results.append(result)
    except ImportError as e:
        logger.error(f"Could not import RemitlyProvider: {e}")

    # Test more providers
    try:
        from apps.providers.ria.integration import RIAProvider

        print("\n=== Testing RIAProvider ===")
        result = test_provider(RIAProvider)
        all_results.append(result)
    except ImportError as e:
        logger.error(f"Could not import RIAProvider: {e}")

    try:
        from apps.providers.transfergo.integration import TransferGoProvider

        print("\n=== Testing TransferGoProvider ===")
        result = test_provider(TransferGoProvider)
        all_results.append(result)
    except ImportError as e:
        logger.error(f"Could not import TransferGoProvider: {e}")

    # Print final summary
    print_test_summary(all_results)

    # If we have at least 2 working providers, test them together
    working_providers = [
        result.get("provider_id") for result in all_results if result.get("success")
    ]
    if len(working_providers) >= 2:
        print(f"\n\n=== Testing Multiple Providers Together ===")
        print(f"Providers: {', '.join(working_providers)}")

        # Import the working provider classes
        provider_classes = []
        for provider_id in working_providers:
            if provider_id == "RemitlyProvider":
                from apps.providers.remitly.integration import RemitlyProvider

                provider_classes.append(RemitlyProvider)
            elif provider_id == "RIAProvider":
                from apps.providers.ria.integration import RIAProvider

                provider_classes.append(RIAProvider)
            elif provider_id == "TransferGoProvider":
                from apps.providers.transfergo.integration import TransferGoProvider

                provider_classes.append(TransferGoProvider)
            elif provider_id == "XEAggregatorProvider":
                from apps.providers.xe.integration import XEAggregatorProvider

                provider_classes.append(XEAggregatorProvider)
            elif provider_id == "WiseProvider":
                from apps.providers.wise.integration import WiseProvider

                provider_classes.append(WiseProvider)

        if provider_classes:
            multi_results = test_multiple_providers(provider_classes)
            print_test_summary(multi_results)


if __name__ == "__main__":
    main()
