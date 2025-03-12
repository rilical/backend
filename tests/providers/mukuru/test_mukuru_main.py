#!/usr/bin/env python3
"""
Test script for the Mukuru provider integration.

This script includes tests for:
1. Direct API calls to test the Mukuru endpoints
2. Testing the provider through the factory
3. Testing the get_quote method with various parameters
4. Comprehensive tests for different corridors and scenarios

Example usage:
    python3 apps/providers/mukuru/tests.py --help
    python3 apps/providers/mukuru/tests.py --api         # Test API endpoints directly
    python3 apps/providers/mukuru/tests.py --factory     # Test through provider factory
    python3 apps/providers/mukuru/tests.py --quote       # Test quote functionality
    python3 apps/providers/mukuru/tests.py --all         # Run all tests
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from decimal import Decimal

import requests

from apps.providers.factory import ProviderFactory
from apps.providers.mukuru.integration import MukuruProvider

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("mukuru_test")

# Define API endpoints directly for direct API testing
BASE_URL = "https://mobile.mukuru.com"
PRICECHECKER_CALCULATE_PATH = "/pricechecker/calculate"
PRICECHECKER_COUNTRIES_PATH = "/pricechecker/get_recipient_countries"

###################
# API Tests
###################


def create_session():
    """Create a basic requests session with headers"""
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15"
            ),
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
        }
    )
    return session


def test_countries_api():
    """
    Test the Mukuru countries API endpoint directly.
    """
    logger.info("Testing Mukuru countries API...")
    session = create_session()

    try:
        url = BASE_URL + PRICECHECKER_COUNTRIES_PATH
        resp = session.get(
            url,
            params={
                "brand_id": 1,
                "sales_channel": "mobi",
            },
            timeout=15,
        )
        resp.raise_for_status()

        try:
            data = resp.json()

            if data:
                # Save the full response to a file for inspection
                output_file = "mukuru_countries_response.json"
                with open(output_file, "w") as f:
                    json.dump(data, f, indent=2)
                logger.info(f"Full countries response saved to {output_file}")

                # Print summary
                print("\nCountries API Response Summary:")
                print("=" * 60)

                if data.get("status") == "success":
                    countries_data = data.get("data", {})
                    print(f"Number of supported countries: {len(countries_data)}")

                    # Print first few countries as examples
                    print("\nSupported countries:")
                    for i, (country_code, info) in enumerate(countries_data.items()):
                        if i < 5:  # Show first 5 countries
                            print(
                                f"  {country_code}: {info.get('country_name', 'Unknown')} "
                                f"({info.get('currency_market_iso', 'Unknown')})"
                            )
                        else:
                            break
                else:
                    print(f"API status: {data.get('status')}")

                return data

            else:
                logger.error("No data returned from countries API")
                return None

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            return None

    except requests.exceptions.RequestException as e:
        logger.error(f"Connection error fetching Mukuru countries: {str(e)}")
        return None


def test_pricechecker_api():
    """
    Test the Mukuru pricechecker API endpoint directly.
    """
    logger.info("Testing Mukuru pricechecker API...")
    session = create_session()

    try:
        url = BASE_URL + PRICECHECKER_CALCULATE_PATH
        params = {
            "from_currency_iso": "ZAR",
            "payin_amount": "900",
            "from_country": "ZA",
            "to_currency_iso": "",
            "payout_amount": "",
            "to_country": "ZW",
            "currency_id": 18,
            "active_input": "payin_amount",
            "brand_id": 1,
            "sales_channel": "mobi",
        }

        resp = session.get(url, params=params, timeout=15)
        resp.raise_for_status()

        try:
            data = resp.json()

            if data:
                # Save the full response to a file for inspection
                output_file = "mukuru_pricechecker_response.json"
                with open(output_file, "w") as f:
                    json.dump(data, f, indent=2)
                logger.info(f"Full pricechecker response saved to {output_file}")

                # Print summary
                print("\nPricechecker API Response Summary:")
                print("=" * 60)

                if data.get("status") == "success":
                    quote_data = data.get("data", {})
                    breakdown = quote_data.get("breakdown", {})

                    print(f"Status: {data.get('status')}")
                    print(f"Payin amount: {quote_data.get('payin_amount')}")
                    print(f"Payout amount: {quote_data.get('payout_amount')}")

                    # Print rate and fee info
                    print(f"\nRate: {breakdown.get('Rate')}")

                    payin_info = breakdown.get("payin", {})
                    print("\nPayin information:")
                    for key, value in payin_info.items():
                        print(f"  {key}: {value}")

                    payout_info = breakdown.get("payout", {})
                    print("\nPayout information:")
                    for key, value in payout_info.items():
                        print(f"  {key}: {value}")
                else:
                    print(f"API status: {data.get('status')}")

                return data

            else:
                logger.error("No data returned from pricechecker API")
                return None

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            return None

    except requests.exceptions.RequestException as e:
        logger.error(f"Connection error fetching Mukuru pricechecker data: {str(e)}")
        return None


def run_api_tests():
    """Run the direct API tests"""
    print("\n" + "=" * 80)
    print("RUNNING DIRECT API TESTS")
    print("=" * 80)

    countries_data = test_countries_api()
    pricechecker_data = test_pricechecker_api()

    return countries_data is not None and pricechecker_data is not None


###################
# Factory Tests
###################


def test_factory():
    """Test the Mukuru provider through the factory"""
    print("\n" + "=" * 80)
    print("RUNNING FACTORY TESTS")
    print("=" * 80)

    try:
        # Get the Mukuru provider from the factory
        provider = ProviderFactory.get_provider("mukuru")

        if provider is None:
            logger.error("Failed to get Mukuru provider from factory")
            return False

        # Get and print supported countries
        countries = provider.get_supported_countries()
        print(
            f"Supported countries: {list(countries.keys())[:5]}... ({len(countries)} total)"
        )

        # Test ZA -> ZW corridor
        rate = provider.get_exchange_rate(
            send_amount=Decimal("900"), send_currency="ZAR", receive_country="ZW"
        )

        # Print the results
        print("\nExchange Rate Result:")
        print("=" * 60)
        for key, value in rate.items():
            print(f"{key}: {value}")

        return True

    except Exception as e:
        logger.error(f"Error in factory test: {str(e)}")
        return False


###################
# Quote Tests
###################


def print_result(result):
    """Print the quote result in a formatted way"""
    print("=" * 60)
    for key, value in result.items():
        print(f"{key}: {value}")


def test_quotes():
    """Test the get_quote method of the Mukuru provider"""
    print("\n" + "=" * 80)
    print("RUNNING QUOTE TESTS")
    print("=" * 80)

    try:
        # Get the Mukuru provider from the factory
        print("Getting Mukuru provider from factory...")
        provider = ProviderFactory.get_provider("mukuru")

        if provider is None:
            logger.error("Failed to get Mukuru provider from factory")
            return False

        # List all available providers
        print(f"Available providers: {ProviderFactory.list_providers()}")

        # Test ZAR -> ZW quote
        print("\nTesting ZAR -> ZW quote:")
        quote = provider.get_quote(
            amount=Decimal("900"), source_currency="ZAR", target_country="ZW"
        )
        print_result(quote)

        # Test ZAR -> GH quote (if supported)
        print("\nTesting ZAR -> GH quote:")
        quote = provider.get_quote(
            amount=Decimal("500"), source_currency="ZAR", target_country="GH"
        )
        print_result(quote)

        return True

    except Exception as e:
        logger.error(f"Error in quote test: {str(e)}")
        return False


###################
# Main Function
###################


def main():
    """Main function to run the tests"""
    parser = argparse.ArgumentParser(description="Test Mukuru provider integration")
    parser.add_argument("--api", action="store_true", help="Run direct API tests")
    parser.add_argument(
        "--factory", action="store_true", help="Run tests through provider factory"
    )
    parser.add_argument(
        "--quote", action="store_true", help="Run tests for the get_quote method"
    )
    parser.add_argument("--all", action="store_true", help="Run all tests")

    args = parser.parse_args()

    print(f"Mukuru Integration Test - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Default to running all tests if no specific tests are requested
    run_all = args.all or not (args.api or args.factory or args.quote)

    success = True

    # Run API tests if requested or if running all tests
    if args.api or run_all:
        api_success = run_api_tests()
        success = success and api_success

    # Run factory tests if requested or if running all tests
    if args.factory or run_all:
        factory_success = test_factory()
        success = success and factory_success

    # Run quote tests if requested or if running all tests
    if args.quote or run_all:
        quote_success = test_quotes()
        success = success and quote_success

    print("\nTests complete.")
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
