#!/usr/bin/env python3
"""
Test script for Western Union delivery methods.

This script tests the delivery method functionality in the WesternUnionProvider,
ensuring that different delivery methods can be specified and used correctly.
"""

import logging
import os
import sys
from decimal import Decimal
from pprint import pprint

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

# Import the provider
from apps.providers.westernunion.integration import WesternUnionProvider
from apps.providers.westernunion.westernunion_mappings import (
    DELIVERY_METHOD_TO_AGGREGATOR,
    DELIVERY_SERVICE_CODES,
    get_delivery_methods_for_country,
    get_service_code_for_delivery_method,
)

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("westernunion_delivery_test")


def test_delivery_methods():
    """Test various delivery methods for different corridors."""
    provider = WesternUnionProvider(timeout=60)

    # Print mapping information for debugging
    print("\n======== DELIVERY METHOD MAPPINGS ========")
    print("Service codes to delivery methods:")
    pprint(DELIVERY_SERVICE_CODES)
    print("\nDelivery methods to aggregator format:")
    pprint(DELIVERY_METHOD_TO_AGGREGATOR)

    # Test case 1: US to Philippines - test all available methods
    print("\n======== Testing US → Philippines ========")

    # First show available delivery methods for Philippines
    delivery_methods = get_delivery_methods_for_country("PH")
    print(f"Available delivery methods for Philippines: {delivery_methods}")
    print(
        f"Mapped to aggregator format: {[DELIVERY_METHOD_TO_AGGREGATOR.get(dm) for dm in delivery_methods]}"
    )

    # For Cash Pickup
    print("\n--- Testing Cash Pickup ---")
    cash_pickup_code = get_service_code_for_delivery_method("cashPickup")
    print(f"Delivery method 'cashPickup' maps to service code: {cash_pickup_code}")

    result = provider.get_quote(
        amount=Decimal("1000"),
        source_currency="USD",
        destination_currency="PHP",
        source_country="US",
        destination_country="PH",
        delivery_method="cashPickup",  # Aggregator format
    )

    if result["success"]:
        print(f"✅ SUCCESS: Exchange Rate = {result['exchange_rate']}")
        print(f"Fee: {result['fee']}")
        print(f"Receive Amount: {result['destination_amount']} {result['destination_currency']}")
        print(f"Delivery Method: {result['delivery_method']}")
    else:
        print(f"❌ FAILED: {result['error_message']}")

    # For Bank Deposit
    print("\n--- Testing Bank Deposit ---")
    bank_deposit_code = get_service_code_for_delivery_method("bankDeposit")
    print(f"Delivery method 'bankDeposit' maps to service code: {bank_deposit_code}")

    result = provider.get_quote(
        amount=Decimal("1000"),
        source_currency="USD",
        destination_currency="PHP",
        source_country="US",
        destination_country="PH",
        delivery_method="bankDeposit",  # Aggregator format
    )

    if result["success"]:
        print(f"✅ SUCCESS: Exchange Rate = {result['exchange_rate']}")
        print(f"Fee: {result['fee']}")
        print(f"Receive Amount: {result['destination_amount']} {result['destination_currency']}")
        print(f"Delivery Method: {result['delivery_method']}")
    else:
        print(f"❌ FAILED: {result['error_message']}")

    # Test case 2: US to Mexico (a common corridor) with Cash Pickup
    print("\n======== Testing US → Mexico with Cash Pickup ========")
    result = provider.get_quote(
        amount=Decimal("1000"),
        source_currency="USD",
        destination_currency="MXN",
        source_country="US",
        destination_country="MX",
        delivery_method="cashPickup",  # Aggregator format
    )

    if result["success"]:
        print(f"✅ SUCCESS: Exchange Rate = {result['exchange_rate']}")
        print(f"Fee: {result['fee']}")
        print(f"Receive Amount: {result['destination_amount']} {result['destination_currency']}")
        print(f"Delivery Method: {result['delivery_method']}")
    else:
        print(f"❌ FAILED: {result['error_message']}")

    # Test case 3: Try a delivery method without specifying one (should use default)
    print("\n======== Testing US → Mexico without specifying delivery method ========")
    result = provider.get_quote(
        amount=Decimal("1000"),
        source_currency="USD",
        destination_currency="MXN",
        source_country="US",
        destination_country="MX",
    )

    if result["success"]:
        print(f"✅ SUCCESS: Exchange Rate = {result['exchange_rate']}")
        print(f"Fee: {result['fee']}")
        print(f"Receive Amount: {result['destination_amount']} {result['destination_currency']}")
        print(f"Delivery Method: {result['delivery_method']}")
    else:
        print(f"❌ FAILED: {result['error_message']}")


if __name__ == "__main__":
    test_delivery_methods()
