#!/usr/bin/env python3
"""
Simplified verification script for Intermex integration.
"""

import json
import os
import sys
from decimal import Decimal

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the provider class
from apps.providers.intermex.integration import IntermexProvider


def run_test():
    """Run basic tests to verify the integration works."""
    print("=== Testing Aggregator-Ready Intermex Integration ===")

    provider = IntermexProvider()

    # Test delivery and payments API
    print("\nTesting delivery and payments endpoint...")
    try:
        # Using the correct parameters from tests.py
        url = f"{provider.BASE_URL}/pricing/api/deliveryandpayments"
        params = {
            "DestCountryAbbr": "MX",
            "DestCurrency": "MXN",
            "OriCountryAbbr": "USA",
            "OriStateAbbr": "NY",
            "ChannelId": "1",
        }

        # Using the correct headers that work with tests.py
        headers = {
            "Pragma": "no-cache",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Origin": "https://www.intermexonline.com",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15",
            "Referer": "https://www.intermexonline.com/",
            "Ocp-Apim-Subscription-Key": "2162a586e2164623a1cd9b6b2d300b4c",
            "LanguageId": "1",
        }

        response = provider.session.get(url, params=params, headers=headers)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print("Delivery Methods:")
            for method in data.get("deliveryMethodsList", []):
                print(
                    f"- {method.get('tranTypeName')} (ID: {method.get('tranTypeId')})"
                )

            print("\nPayment Methods:")
            for method in data.get("paymentMethods", []):
                print(
                    f"- {method.get('senderPaymentMethodName')} (Fee: ${method.get('feeAmount')})"
                )
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error in delivery/payments test: {e}")

    # Test get_delivery_methods aggregator method
    print("\nTesting get_delivery_methods aggregator method...")
    try:
        delivery_methods = provider.get_delivery_methods(
            source_country="US",
            dest_country="MX",
            source_currency="USD",
            dest_currency="MXN",
        )
        print(f"Success: {delivery_methods['success']}")
        print("Available Delivery Methods:")
        for method in delivery_methods.get("delivery_methods", []):
            print(f"- {method['name']} (ID: {method['id']})")

        print("\nAvailable Payment Methods:")
        for method in delivery_methods.get("payment_methods", []):
            print(f"- {method['name']} (Fee: ${method['fee']})")
    except Exception as e:
        print(f"Error in get_delivery_methods test: {e}")

    # Test get_quote aggregator method
    print("\nTesting get_quote aggregator method...")
    try:
        quote = provider.get_quote(
            send_amount=1000.0,
            send_currency="USD",
            receive_currency="MXN",
            send_country="US",
            receive_country="MX",
            payment_method="debitCard",
            delivery_method="cashPickup",
        )
        print(f"Success: {quote['success']}")
        if quote["success"]:
            print(f"Exchange Rate: {quote['exchange_rate']}")
            print(f"Send: {quote['send_amount']} {quote['source_currency']}")
            print(
                f"Receive: {quote['destination_amount']} {quote['destination_currency']}"
            )
            print(f"Fee: ${quote['fee']}")

            if "available_payment_methods" in quote:
                print("\nAvailable Payment Methods:")
                for method_id, details in quote["available_payment_methods"].items():
                    print(f"- {details['name']}: ${details['fee']}")
        else:
            print(f"Error: {quote.get('error_message', 'Unknown error')}")
    except Exception as e:
        print(f"Error in get_quote test: {e}")

    # Test get_exchange_rate aggregator method
    print("\nTesting get_exchange_rate aggregator method...")
    try:
        rate = provider.get_exchange_rate(
            send_currency="USD",
            receive_currency="MXN",
            send_country="US",
            receive_country="MX",
            amount=Decimal("1000.00"),
        )
        print(f"Success: {rate['success']}")
        if rate["success"]:
            print(f"Exchange Rate: {rate['rate']}")
            print(f"Fee: ${rate['fee']}")
            print(f"Source Currency: {rate['source_currency']}")
            print(f"Target Currency: {rate['target_currency']}")
        else:
            print(f"Error: {rate.get('error_message', 'Unknown error')}")
    except Exception as e:
        print(f"Error in get_exchange_rate test: {e}")

    print("\n=== Testing Complete ===")


if __name__ == "__main__":
    run_test()
