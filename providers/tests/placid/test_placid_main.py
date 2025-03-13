#!/usr/bin/env python3
"""
Placid Provider Test Script

This script provides comprehensive testing for the Placid provider integration, including:
- Direct API calls to verify endpoints are working
- Factory tests to verify the provider is correctly registered and functioning
- Quote tests using the get_quote method
- Comprehensive tests with various currency pairs, amounts, and edge cases
- Error handling tests to verify proper behavior with invalid inputs

Usage:
    python tests.py [--api] [--factory] [--quote] [--comprehensive] [--errors] [--all] [--help]
"""

import argparse
import json
import logging
import os
import re
import sys
import time
from datetime import datetime
from decimal import Decimal

import requests

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("placid-tests")

# API Endpoints for direct testing
BASE_URL = "https://www.placid.net"
ENDPOINT = "/conf/sqls/pstRqstNS.php"

# Test corridors and their expected currencies
TEST_CORRIDORS = {
    "PAK": "PKR",  # Pakistan - Pakistani Rupee
    "IND": "INR",  # India - Indian Rupee
    "BGD": "BDT",  # Bangladesh - Bangladesh Taka
    "PHL": "PHP",  # Philippines - Philippine Peso
    "NPL": "NPR",  # Nepal - Nepalese Rupee
    "LKA": "LKR",  # Sri Lanka - Sri Lankan Rupee
    "IDN": "IDR",  # Indonesia - Indonesian Rupiah
    "VNM": "VND",  # Vietnam - Vietnamese Dong
}

# Test source countries
TEST_SOURCE_COUNTRIES = ["US", "GB", "EU", "CA", "AU"]

# Save output directory for API responses
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ======= API Test Functions =======


def create_session():
    """Create and return a requests session with appropriate headers."""
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                "Version/18.3 Safari/605.1.15"
            ),
            "Accept": "*/*",
            "Content-Type": "application/x-www-form-urlencoded",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
    )
    return session


def test_corridor_api(corridor_val="PAK", task_type="ChgContIndx", retry_count=1):
    """
    Test the corridor API endpoint.

    Args:
        corridor_val: Corridor value to test (e.g., "PAK")
        task_type: Task type for the API request
        retry_count: Number of retries on failure

    Returns:
        Tuple of (success, rate, response_text)
    """
    session = create_session()

    # Get a current timestamp for rndval
    rndval = str(int(time.time() * 1000))

    # Build the query params
    query_params = {
        "TaskType": task_type,
        "Val1": corridor_val,
        "Val2": "NIL",
        "Val3": "NIL",
        "Val4": "NIL",
        "Val5": "NIL",
        "Val6": "NIL",
    }

    # Build the POST data
    data = {
        "rndval": rndval,
    }

    url = BASE_URL + ENDPOINT
    logger.info(f"Testing Placid corridor API: {url} with corridor={corridor_val}")

    for attempt in range(retry_count):
        try:
            response = session.post(url, params=query_params, data=data, timeout=15)
            response.raise_for_status()

            content = response.text
            logger.info(f"API response content (first 300 chars): {content[:300]}...")

            # Save response to file
            filename = os.path.join(
                OUTPUT_DIR,
                f"corridor_response_{corridor_val}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
            )
            with open(filename, "w") as f:
                f.write(content)
            logger.info(f"Response saved to {filename}")

            # Check if we got a valid response with the corridor value
            if corridor_val in content:
                logger.info(f"✅ Found corridor {corridor_val} in response")

                # Try to extract the exchange rate if available
                currency_code = TEST_CORRIDORS.get(corridor_val, corridor_val)
                pattern = rf"(\d+\.\d+)\s*{currency_code}"
                match = re.search(pattern, content)

                if match:
                    rate = float(match.group(1))
                    logger.info(f"✅ Found exchange rate: {rate} {currency_code}")
                    return True, rate, content
                else:
                    logger.warning(
                        f"⚠️ Could not find exchange rate for {currency_code} in response"
                    )
                    return True, None, content
            else:
                logger.error(f"❌ Corridor {corridor_val} not found in response")

                if attempt < retry_count - 1:
                    logger.info(f"Retrying... (Attempt {attempt + 2} of {retry_count})")
                    time.sleep(2)  # Wait 2 seconds before retrying
                else:
                    return False, None, content

        except Exception as e:
            logger.error(f"API test failed: {str(e)}")

            if attempt < retry_count - 1:
                logger.info(f"Retrying... (Attempt {attempt + 2} of {retry_count})")
                time.sleep(2)  # Wait 2 seconds before retrying
            else:
                return False, None, str(e)

    return False, None, "Max retries reached"


def test_task_types():
    """Test different task types to see what they return."""
    task_types = ["ChgContIndx", "RateTable", "GetContent", "GetCountries"]
    results = []

    for task_type in task_types:
        logger.info(f"\nTesting task type: {task_type}")
        success, rate, content = test_corridor_api("PAK", task_type)
        results.append(
            {
                "task_type": task_type,
                "success": success,
                "rate": rate,
                "content_length": len(content) if content else 0,
            }
        )

    # Print summary
    logger.info("\nTask Type Test Results:")
    for result in results:
        status = "✅" if result["success"] else "❌"
        logger.info(
            f"{status} {result['task_type']}: Success={result['success']}, Rate={result['rate']}, Content Length={result['content_length']}"
        )

    return any(r["success"] for r in results)


def run_api_tests():
    """Run all API tests."""
    logger.info("Running Placid API tests")

    # Test all corridors
    corridor_results = []
    for corridor in TEST_CORRIDORS.keys():
        success, rate, _ = test_corridor_api(corridor, retry_count=2)
        corridor_results.append(
            {
                "corridor": corridor,
                "currency": TEST_CORRIDORS.get(corridor),
                "success": success,
                "rate": rate,
            }
        )

    # Print summary
    logger.info("\nCorridor Test Results:")
    success_count = 0
    for result in corridor_results:
        status = "✅" if result["success"] else "❌"
        rate_info = f", Rate={result['rate']}" if result["rate"] else ""
        logger.info(
            f"{status} {result['corridor']} ({result['currency']}): Success={result['success']}{rate_info}"
        )
        if result["success"]:
            success_count += 1

    # Test different task types
    task_type_success = test_task_types()

    # Overall API test success
    if success_count > 0 and task_type_success:
        logger.info(
            f"✅ API tests passed for {success_count}/{len(corridor_results)} corridors and task types"
        )
        return True
    else:
        logger.error("❌ All API tests failed")
        return False


# ======= Factory Test Functions =======


def test_factory():
    """Test the Placid provider through the factory."""
    try:
        from providers import get_provider_by_name, list_providers
        from providers.placid import PlacidProvider

        # Get provider from factory
        provider = get_provider_by_name("placid")
        logger.info(f"Provider type: {type(provider)}")

        # Verify provider is of correct type
        if not isinstance(provider, PlacidProvider):
            logger.error(f"Provider is not a PlacidProvider: {type(provider)}")
            return False

        # Make sure Placid is in the list of providers
        providers = list_providers()
        if "placid" not in providers:
            logger.error(f"Placid provider not found in provider list: {providers}")
            return False

        # Test get_exchange_rate with multiple corridors
        success_count = 0
        test_corridors = list(TEST_CORRIDORS.keys())[:3]  # Test first 3 corridors

        for corridor in test_corridors:
            logger.info(f"\nTesting factory get_exchange_rate with corridor: {corridor}")
            result = provider.get_exchange_rate(source_country="US", corridor_val=corridor)

            logger.info(f"Exchange rate result: {result}")

            if result.get("success"):
                logger.info(f"✅ Successful rate for {corridor}: {result.get('rate')}")
                success_count += 1
            else:
                logger.warning(
                    f"⚠️ Failed to get rate for {corridor}: {result.get('error_message')}"
                )

        if success_count > 0:
            logger.info(
                f"✅ Factory tests passed for {success_count}/{len(test_corridors)} corridors"
            )
            return True
        else:
            logger.error("❌ All factory tests failed")
            return False

    except ImportError as e:
        logger.error(f"Import error: {str(e)}")
        logger.info(
            "Make sure the provider is registered in the factory and all dependencies are installed."
        )
        return False

    except Exception as e:
        logger.error(f"Factory test error: {str(e)}")
        return False


# ======= Quote Test Functions =======


def print_result(result):
    """Print the result of a quote in a formatted way."""
    if result.get("success"):
        logger.info(
            f"✅ Quote Success: {result['send_amount']} {result.get('source_currency', 'source')} → "
            f"{result.get('receive_amount')} {result.get('target_currency', 'target')}"
        )
        logger.info(f"   Exchange Rate: {result.get('exchange_rate')}")
    else:
        logger.error(f"❌ Quote Failed: {result.get('error_message')}")


def test_quotes():
    """Test the get_quote method of the PlacidProvider with various scenarios."""
    try:
        from decimal import Decimal

        from providers import get_provider_by_name

        provider = get_provider_by_name("placid")
        success_count = 0
        total_tests = 0

        # Test with various source currencies and amounts
        source_currencies = ["USD", "GBP", "EUR"]
        amounts = [Decimal("100.00"), Decimal("1000.00")]

        # Test first 3 corridors only to avoid excessive API calls
        target_currencies = [TEST_CORRIDORS[k] for k in list(TEST_CORRIDORS.keys())[:3]]

        for source_currency in source_currencies:
            for target_currency in target_currencies:
                for amount in amounts:
                    total_tests += 1

                    logger.info(
                        f"\nTest: Converting {amount} {source_currency} to {target_currency}"
                    )
                    result = provider.get_quote(
                        amount=amount,
                        source_currency=source_currency,
                        target_currency=target_currency,
                    )
                    print_result(result)

                    if result.get("success"):
                        success_count += 1

        # Test unsupported currency
        total_tests += 1
        logger.info("\nTest: Testing unsupported currency pair - USD to XYZ")
        result = provider.get_quote(
            amount=Decimal("1000.00"), source_currency="USD", target_currency="XYZ"
        )
        print_result(result)

        # Success is expected to be False for invalid currency
        if not result.get("success") and "error_message" in result:
            logger.info("✅ Correctly handled invalid currency")
            success_count += 1

        logger.info(f"\nQuote Tests: {success_count}/{total_tests} successful")
        return success_count > 0

    except Exception as e:
        logger.error(f"Quote test error: {str(e)}")
        return False


# ======= Comprehensive Tests =======


def run_comprehensive_tests():
    """Run a comprehensive series of tests on the Placid provider."""
    try:
        import random
        from decimal import Decimal

        from providers import get_provider_by_name

        provider = get_provider_by_name("placid")

        # Test with all combinations of:
        # - Source countries/currencies
        # - Target corridors/currencies
        # - Various amounts, including edge cases

        # Source currencies and corresponding countries
        source_data = [
            {"currency": "USD", "country": "US"},
            {"currency": "GBP", "country": "GB"},
            {"currency": "EUR", "country": "EU"},
            {"currency": "CAD", "country": "CA"},
            {"currency": "AUD", "country": "AU"},
        ]

        # Target corridors and currencies (use all corridors)
        target_data = [
            {"corridor": corridor, "currency": currency}
            for corridor, currency in TEST_CORRIDORS.items()
        ]

        # Test amounts, including edge cases
        amounts = [
            Decimal("1.00"),  # Very small amount
            Decimal("100.00"),  # Small amount
            Decimal("1000.00"),  # Medium amount
            Decimal("10000.00"),  # Large amount
            Decimal("9999.99"),  # Near edge amount
            Decimal("1234.56"),  # Random amount
        ]

        # Select subset of tests to avoid too many API calls
        # For a full test, you could use all combinations
        max_tests = 20
        combined_tests = []

        for _ in range(max_tests):
            source = random.choice(source_data)
            target = random.choice(target_data)
            amount = random.choice(amounts)

            combined_tests.append(
                {
                    "source_currency": source["currency"],
                    "source_country": source["country"],
                    "target_corridor": target["corridor"],
                    "target_currency": target["currency"],
                    "amount": amount,
                }
            )

        # Add some fixed tests to ensure coverage
        combined_tests.extend(
            [
                # Basic USD to PKR
                {
                    "source_currency": "USD",
                    "source_country": "US",
                    "target_corridor": "PAK",
                    "target_currency": "PKR",
                    "amount": Decimal("1000.00"),
                },
                # GBP to INR
                {
                    "source_currency": "GBP",
                    "source_country": "GB",
                    "target_corridor": "IND",
                    "target_currency": "INR",
                    "amount": Decimal("500.00"),
                },
                # EUR to BDT
                {
                    "source_currency": "EUR",
                    "source_country": "EU",
                    "target_corridor": "BGD",
                    "target_currency": "BDT",
                    "amount": Decimal("750.00"),
                },
            ]
        )

        success_count = 0
        total_tests = len(combined_tests)

        for i, test in enumerate(combined_tests):
            logger.info(
                f"\nComprehensive Test {i+1}/{total_tests}: "
                f"{test['amount']} {test['source_currency']} → {test['target_currency']} "
                f"(Source: {test['source_country']}, Corridor: {test['target_corridor']})"
            )

            # First try the direct exchange_rate method
            rate_result = provider.get_exchange_rate(
                source_country=test["source_country"],
                corridor_val=test["target_corridor"],
            )

            if rate_result.get("success"):
                logger.info(f"✅ Direct exchange rate successful: {rate_result.get('rate')}")
            else:
                logger.warning(
                    f"⚠️ Direct exchange rate failed: {rate_result.get('error_message')}"
                )

            # Then try the quote method
            quote_result = provider.get_quote(
                amount=test["amount"],
                source_currency=test["source_currency"],
                target_currency=test["target_currency"],
                source_country=test["source_country"],
            )

            print_result(quote_result)

            if quote_result.get("success"):
                success_count += 1

                # Verify calculation correctness
                send_amount = float(test["amount"])
                rate = quote_result.get("exchange_rate")
                calculated_receive = send_amount * rate
                actual_receive = quote_result.get("receive_amount")

                if (
                    abs(calculated_receive - actual_receive) < 0.01
                ):  # Allow small rounding differences
                    logger.info("✅ Receive amount calculation is correct")
                else:
                    logger.warning(
                        f"⚠️ Calculation mismatch: {calculated_receive} != {actual_receive}"
                    )

        logger.info(f"\nComprehensive Tests: {success_count}/{total_tests} successful")
        return success_count > 0  # Consider test passed if at least one quote was successful

    except Exception as e:
        logger.error(f"Comprehensive test error: {str(e)}")
        return False


# ======= Error Handling Tests =======


def test_error_handling():
    """Test error handling in the PlacidProvider."""
    try:
        from decimal import Decimal

        from providers import get_provider_by_name
        from providers.placid.exceptions import PlacidError

        provider = get_provider_by_name("placid")

        error_tests = [
            # Test with invalid corridor
            {
                "test_name": "Invalid Corridor",
                "params": {
                    "source_country": "US",
                    "corridor_val": "XYZ",  # Invalid corridor
                },
                "expect_success": False,
            },
            # Test with invalid source country
            {
                "test_name": "Invalid Source Country",
                "params": {
                    "source_country": "INVALID",
                    "corridor_val": "PAK",
                },
                "expect_success": False,
            },
            # Test with empty corridor
            {
                "test_name": "Empty Corridor",
                "params": {
                    "source_country": "US",
                    "corridor_val": "",  # Empty corridor
                },
                "expect_success": False,
            },
            # Test with invalid rndval
            {
                "test_name": "Invalid rndval",
                "params": {
                    "source_country": "US",
                    "corridor_val": "PAK",
                    "rndval": "invalid",  # Invalid rndval
                },
                "expect_success": False,
            },
        ]

        success_count = 0
        total_tests = len(error_tests)

        for i, test in enumerate(error_tests):
            logger.info(f"\nError Test {i+1}/{total_tests}: {test['test_name']}")

            try:
                result = provider.get_exchange_rate(**test["params"])

                # Check if the success status matches our expectation
                if result.get("success") == test["expect_success"]:
                    logger.info(f"✅ Test passed: success={result.get('success')}")
                    if not result.get("success"):
                        logger.info(f"   Error message: {result.get('error_message')}")
                    success_count += 1
                else:
                    logger.error(
                        f"❌ Test failed: Expected success={test['expect_success']}, got {result.get('success')}"
                    )
                    logger.error(f"   Result: {result}")

            except PlacidError as e:
                # If we expect an error and got a PlacidError, that's a success
                if not test["expect_success"]:
                    logger.info(f"✅ Test passed: Caught expected PlacidError: {str(e)}")
                    success_count += 1
                else:
                    logger.error(f"❌ Test failed: Unexpected PlacidError: {str(e)}")

            except Exception as e:
                logger.error(f"❌ Test failed: Unexpected error: {str(e)}")

        # Check get_quote error handling
        quote_error_tests = [
            # Test with invalid target currency
            {
                "test_name": "Invalid Target Currency",
                "params": {
                    "amount": Decimal("1000.00"),
                    "source_currency": "USD",
                    "target_currency": "XYZ",  # Invalid currency
                },
                "expect_success": False,
            },
            # Test with invalid source currency
            {
                "test_name": "Invalid Source Currency",
                "params": {
                    "amount": Decimal("1000.00"),
                    "source_currency": "XYZ",  # Invalid currency
                    "target_currency": "PKR",
                },
                "expect_success": False,
            },
            # Test with negative amount
            {
                "test_name": "Negative Amount",
                "params": {
                    "amount": Decimal("-1000.00"),  # Negative amount
                    "source_currency": "USD",
                    "target_currency": "PKR",
                },
                "expect_success": False,
            },
        ]

        total_tests += len(quote_error_tests)

        for i, test in enumerate(quote_error_tests):
            logger.info(f"\nQuote Error Test {i+1}/{len(quote_error_tests)}: {test['test_name']}")

            try:
                result = provider.get_quote(**test["params"])

                # Check if the success status matches our expectation
                if result.get("success") == test["expect_success"]:
                    logger.info(f"✅ Test passed: success={result.get('success')}")
                    if not result.get("success"):
                        logger.info(f"   Error message: {result.get('error_message')}")
                    success_count += 1
                else:
                    logger.error(
                        f"❌ Test failed: Expected success={test['expect_success']}, got {result.get('success')}"
                    )
                    logger.error(f"   Result: {result}")

            except PlacidError as e:
                # If we expect an error and got a PlacidError, that's a success
                if not test["expect_success"]:
                    logger.info(f"✅ Test passed: Caught expected PlacidError: {str(e)}")
                    success_count += 1
                else:
                    logger.error(f"❌ Test failed: Unexpected PlacidError: {str(e)}")

            except Exception as e:
                logger.error(f"❌ Test failed: Unexpected error: {str(e)}")

        logger.info(f"\nError Handling Tests: {success_count}/{total_tests} successful")
        return success_count > 0

    except Exception as e:
        logger.error(f"Error handling test error: {str(e)}")
        return False


# ======= Main Function =======


def main():
    """Main function to parse arguments and run tests."""
    parser = argparse.ArgumentParser(description="Test the Placid provider")
    parser.add_argument("--api", action="store_true", help="Run API tests")
    parser.add_argument("--factory", action="store_true", help="Run factory tests")
    parser.add_argument("--quote", action="store_true", help="Run quote tests")
    parser.add_argument("--comprehensive", action="store_true", help="Run comprehensive tests")
    parser.add_argument("--errors", action="store_true", help="Run error handling tests")
    parser.add_argument("--all", action="store_true", help="Run all tests")

    args = parser.parse_args()

    # If no arguments provided, show help
    if len(sys.argv) == 1:
        parser.print_help()
        return

    success = True

    if args.api or args.all:
        logger.info("\n=========== RUNNING API TESTS ===========")
        api_success = run_api_tests()
        success = success and api_success

    if args.factory or args.all:
        logger.info("\n=========== RUNNING FACTORY TESTS ===========")
        factory_success = test_factory()
        success = success and factory_success

    if args.quote or args.all:
        logger.info("\n=========== RUNNING QUOTE TESTS ===========")
        quote_success = test_quotes()
        success = success and quote_success

    if args.comprehensive or args.all:
        logger.info("\n=========== RUNNING COMPREHENSIVE TESTS ===========")
        comprehensive_success = run_comprehensive_tests()
        success = success and comprehensive_success

    if args.errors or args.all:
        logger.info("\n=========== RUNNING ERROR HANDLING TESTS ===========")
        error_success = test_error_handling()
        success = success and error_success

    if success:
        logger.info("\n✅ All requested tests passed!")
        sys.exit(0)
    else:
        logger.error("\n❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
