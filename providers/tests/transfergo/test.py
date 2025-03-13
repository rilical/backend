#!/usr/bin/env python3
"""
Test script for TransferGo provider integration.
"""

import json
import logging
import os
import sys
from decimal import Decimal

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from providers.transferGo.integration import TransferGoProvider

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def test_exchange_rate():
    """Test getting exchange rates from TransferGo."""

    print("=" * 80)
    print("TESTING TRANSFERGO INTEGRATION - BASIC CORRIDORS")
    print("=" * 80)

    # Example corridors to test
    test_cases = [
        # EUR corridors (TransferGo's primary market)
        {
            "name": "EUR to Ukraine (UAH)",
            "send_amount": Decimal("500.00"),
            "send_currency": "EUR",
            "receive_country": "UA",
            "receive_currency": "UAH",
        },
        {
            "name": "EUR to Poland (PLN)",
            "send_amount": Decimal("300.00"),
            "send_currency": "EUR",
            "receive_country": "PL",
            "receive_currency": "PLN",
        },
        {
            "name": "EUR to Romania (RON)",
            "send_amount": Decimal("400.00"),
            "send_currency": "EUR",
            "receive_country": "RO",
            "receive_currency": "RON",
        },
        # GBP corridors
        {
            "name": "GBP to India (INR)",
            "send_amount": Decimal("600.00"),
            "send_currency": "GBP",
            "receive_country": "IN",
            "receive_currency": "INR",
        },
        {
            "name": "GBP to Philippines (PHP)",
            "send_amount": Decimal("500.00"),
            "send_currency": "GBP",
            "receive_country": "PH",
            "receive_currency": "PHP",
        },
        # Other common corridors
        {
            "name": "USD to Mexico (MXN)",
            "send_amount": Decimal("800.00"),
            "send_currency": "USD",
            "receive_country": "MX",
            "receive_currency": "MXN",
        },
        {
            "name": "USD to Vietnam (VND)",
            "send_amount": Decimal("700.00"),
            "send_currency": "USD",
            "receive_country": "VN",
            "receive_currency": "VND",
        },
    ]

    # Initialize TransferGo provider
    transfergo = TransferGoProvider()

    # Test each corridor
    for test_case in test_cases:
        print(f"\nTesting: {test_case['name']}")
        print("-" * 50)

        try:
            result = transfergo.get_exchange_rate(
                send_amount=test_case["send_amount"],
                send_currency=test_case["send_currency"],
                receive_country=test_case["receive_country"],
                receive_currency=test_case["receive_currency"],
            )

            # Print formatted result
            print(f"Source amount: {result['source_amount']} {result['source_currency']}")
            print(
                f"Destination amount: {result['destination_amount']} {result['destination_currency']}"
            )
            print(f"Exchange rate: {result['exchange_rate']}")
            print(f"Fee: {result['fee']} {result['source_currency']}")
            print(f"Delivery method: {result['delivery_method']}")
            print(f"Payment method: {result['payment_method']}")
            print(f"Corridor: {result['corridor']}")

            # Check if this is fallback data
            if result.get("details", {}).get("is_fallback", False):
                print(f"⚠️ NOTE: Using fallback/estimated rates (API request failed)")
            else:
                print(f"✅ SUCCESS: Using live API rates")
                # Print booking token if available
                booking_token = result.get("details", {}).get("booking_token")
                if booking_token:
                    print(f"Booking token: {booking_token[:15]}...")  # Show first 15 chars

            # Print delivery time if available
            delivery_time_minutes = result.get("delivery_time_minutes")
            if delivery_time_minutes:
                hours = delivery_time_minutes // 60
                minutes = delivery_time_minutes % 60

                if hours > 0:
                    print(f"Estimated delivery time: {hours} hour(s) {minutes} minute(s)")
                else:
                    print(f"Estimated delivery time: {minutes} minute(s)")

        except Exception as e:
            print(f"Error: {e}")

    print("\nTest completed.")


def test_new_countries_and_currencies():
    """Test getting exchange rates for newly added countries and currencies."""

    print("=" * 80)
    print("TESTING TRANSFERGO INTEGRATION - NEW COUNTRIES AND CURRENCIES")
    print("=" * 80)

    # Test cases for new countries/currencies
    test_cases = [
        # Middle East
        {
            "name": "EUR to United Arab Emirates (AED)",
            "send_amount": Decimal("1000.00"),
            "send_currency": "EUR",
            "receive_country": "AE",
            "receive_currency": "AED",
        },
        {
            "name": "GBP to Saudi Arabia (SAR)",
            "send_amount": Decimal("800.00"),
            "send_currency": "GBP",
            "receive_country": "SA",
            "receive_currency": "SAR",
        },
        {
            "name": "USD to Israel (ILS)",
            "send_amount": Decimal("750.00"),
            "send_currency": "USD",
            "receive_country": "IL",
            "receive_currency": "ILS",
        },
        # Asia Pacific
        {
            "name": "USD to Japan (JPY)",
            "send_amount": Decimal("500.00"),
            "send_currency": "USD",
            "receive_country": "JP",
            "receive_currency": "JPY",
        },
        {
            "name": "EUR to Singapore (SGD)",
            "send_amount": Decimal("600.00"),
            "send_currency": "EUR",
            "receive_country": "SG",
            "receive_currency": "SGD",
        },
        {
            "name": "GBP to Thailand (THB)",
            "send_amount": Decimal("700.00"),
            "send_currency": "GBP",
            "receive_country": "TH",
            "receive_currency": "THB",
        },
        # Africa
        {
            "name": "EUR to Kenya (KES)",
            "send_amount": Decimal("400.00"),
            "send_currency": "EUR",
            "receive_country": "KE",
            "receive_currency": "KES",
        },
        {
            "name": "GBP to Ghana (GHS)",
            "send_amount": Decimal("500.00"),
            "send_currency": "GBP",
            "receive_country": "GH",
            "receive_currency": "GHS",
        },
        # Americas
        {
            "name": "USD to Brazil (BRL)",
            "send_amount": Decimal("600.00"),
            "send_currency": "USD",
            "receive_country": "BR",
            "receive_currency": "BRL",
        },
        {
            "name": "EUR to Colombia (COP)",
            "send_amount": Decimal("450.00"),
            "send_currency": "EUR",
            "receive_country": "CO",
            "receive_currency": "COP",
        },
    ]

    # Initialize TransferGo provider
    transfergo = TransferGoProvider()

    # Test each corridor
    for test_case in test_cases:
        print(f"\nTesting: {test_case['name']}")
        print("-" * 50)

        try:
            result = transfergo.get_exchange_rate(
                send_amount=test_case["send_amount"],
                send_currency=test_case["send_currency"],
                receive_country=test_case["receive_country"],
                receive_currency=test_case["receive_currency"],
            )

            # Print formatted result
            print(f"Source amount: {result['source_amount']} {result['source_currency']}")
            print(
                f"Destination amount: {result['destination_amount']} {result['destination_currency']}"
            )
            print(f"Exchange rate: {result['exchange_rate']}")
            print(f"Fee: {result['fee']} {result['source_currency']}")
            print(f"Corridor: {result['corridor']}")

            # Check if this is fallback data
            if result.get("details", {}).get("is_fallback", False):
                print(f"⚠️ NOTE: Using fallback/estimated rates (API request failed)")
            else:
                print(f"✅ SUCCESS: Using live API rates")

        except Exception as e:
            print(f"Error: {e}")

    print("\nTest completed.")


def test_multi_currency_countries():
    """Test countries that support multiple receiving currencies."""

    print("=" * 80)
    print("TESTING TRANSFERGO INTEGRATION - MULTI-CURRENCY COUNTRIES")
    print("=" * 80)

    # Test cases for multi-currency countries
    multi_currency_tests = [
        # Ukraine with different currencies
        {
            "name": "EUR to Ukraine (UAH - default)",
            "send_amount": Decimal("500.00"),
            "send_currency": "EUR",
            "receive_country": "UA",
        },
        {
            "name": "EUR to Ukraine (USD - preferred)",
            "send_amount": Decimal("500.00"),
            "send_currency": "EUR",
            "receive_country": "UA",
            "preferred_receive_currency": "USD",
        },
        {
            "name": "EUR to Ukraine (EUR - preferred)",
            "send_amount": Decimal("500.00"),
            "send_currency": "EUR",
            "receive_country": "UA",
            "preferred_receive_currency": "EUR",
        },
        # India with different currencies
        {
            "name": "GBP to India (INR - default)",
            "send_amount": Decimal("600.00"),
            "send_currency": "GBP",
            "receive_country": "IN",
        },
        {
            "name": "GBP to India (USD - preferred)",
            "send_amount": Decimal("600.00"),
            "send_currency": "GBP",
            "receive_country": "IN",
            "preferred_receive_currency": "USD",
        },
        # Other multi-currency countries
        {
            "name": "USD to Philippines (PHP - default)",
            "send_amount": Decimal("700.00"),
            "send_currency": "USD",
            "receive_country": "PH",
        },
        {
            "name": "USD to Philippines (USD - preferred)",
            "send_amount": Decimal("700.00"),
            "send_currency": "USD",
            "receive_country": "PH",
            "preferred_receive_currency": "USD",
        },
        {
            "name": "EUR to Kenya (KES - default)",
            "send_amount": Decimal("400.00"),
            "send_currency": "EUR",
            "receive_country": "KE",
        },
        {
            "name": "EUR to Kenya (USD - preferred)",
            "send_amount": Decimal("400.00"),
            "send_currency": "EUR",
            "receive_country": "KE",
            "preferred_receive_currency": "USD",
        },
    ]

    # Initialize TransferGo provider
    transfergo = TransferGoProvider()

    # Test each multi-currency case
    for test_case in multi_currency_tests:
        print(f"\nTesting: {test_case['name']}")
        print("-" * 50)

        try:
            # Check if preferred currency is specified
            kwargs = {}
            if "preferred_receive_currency" in test_case:
                kwargs["preferred_receive_currency"] = test_case["preferred_receive_currency"]

            result = transfergo.get_exchange_rate(
                send_amount=test_case["send_amount"],
                send_currency=test_case["send_currency"],
                receive_country=test_case["receive_country"],
                **kwargs,
            )

            # Print formatted result
            print(f"Source amount: {result['source_amount']} {result['source_currency']}")
            print(
                f"Destination amount: {result['destination_amount']} {result['destination_currency']}"
            )
            print(f"Exchange rate: {result['exchange_rate']}")
            print(f"Fee: {result['fee']} {result['source_currency']}")
            print(f"Corridor: {result['corridor']}")

            # Check if the preferred currency was used
            if "preferred_receive_currency" in test_case:
                if result["destination_currency"] == test_case["preferred_receive_currency"]:
                    print(
                        f"✅ Preferred currency ({test_case['preferred_receive_currency']}) was used successfully"
                    )
                else:
                    print(
                        f"❌ Preferred currency ({test_case['preferred_receive_currency']}) was not used. Using {result['destination_currency']} instead"
                    )

            # Check if this is fallback data
            if result.get("details", {}).get("is_fallback", False):
                print(f"⚠️ NOTE: Using fallback/estimated rates (API request failed)")
            else:
                print(f"✅ SUCCESS: Using live API rates")

        except Exception as e:
            print(f"Error: {e}")

    print("\nTest completed.")


def test_supported_countries_and_currencies():
    """Test retrieving all supported countries and currencies."""

    print("=" * 80)
    print("TESTING TRANSFERGO SUPPORTED COUNTRIES AND CURRENCIES")
    print("=" * 80)

    # Initialize TransferGo provider
    transfergo = TransferGoProvider()

    # Get all supported countries and currencies
    countries_currencies = transfergo.get_supported_countries_and_currencies()

    # Get sending countries
    send_countries = transfergo.get_supported_send_countries()

    # Print statistics
    total_countries = len(countries_currencies)
    total_currencies = len(
        set([curr for curr_list in countries_currencies.values() for curr in curr_list])
    )
    multi_currency_countries = [
        country for country, currencies in countries_currencies.items() if len(currencies) > 1
    ]

    print(f"Total supported receiving countries: {total_countries}")
    print(f"Total supported currencies: {total_currencies}")
    print(f"Total sending countries: {len(send_countries)}")
    print(f"Countries with multiple currency options: {len(multi_currency_countries)}")

    # Print multi-currency countries
    print("\nMulti-currency countries:")
    for country in multi_currency_countries:
        print(f"{country}: {', '.join(countries_currencies[country])}")

    print("\nSending countries:")
    # Print sending countries in neat columns
    columns = 5
    send_country_chunks = [
        send_countries[i : i + columns] for i in range(0, len(send_countries), columns)
    ]
    for chunk in send_country_chunks:
        print("  ".join(f"{country}" for country in chunk))

    print("\nTest completed.")


if __name__ == "__main__":
    print("Select a test to run:")
    print("1. Basic corridors")
    print("2. New countries and currencies")
    print("3. Multi-currency countries")
    print("4. Supported countries and currencies")
    print("5. Run all tests")

    choice = input("Enter choice (1-5): ")

    if choice == "1":
        test_exchange_rate()
    elif choice == "2":
        test_new_countries_and_currencies()
    elif choice == "3":
        test_multi_currency_countries()
    elif choice == "4":
        test_supported_countries_and_currencies()
    elif choice == "5":
        test_exchange_rate()
        test_new_countries_and_currencies()
        test_multi_currency_countries()
        test_supported_countries_and_currencies()
    else:
        print("Invalid choice. Exiting.")
