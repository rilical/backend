#!/usr/bin/env python3
"""
Test script for OrbitRemit integration.

This script provides comprehensive tests for the OrbitRemit provider, including:
1. Direct API tests (testing the raw OrbitRemit API)
2. Factory tests (testing the provider through the factory)
3. Fee tests (testing the get_fee_info method)
4. Quote tests (testing the get_quote method)
5. Error handling tests (testing error conditions)

Usage:
    python tests.py [--api] [--factory] [--fee] [--quote] [--errors] [--all] [--help]
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from decimal import Decimal

import requests

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("orbitremit-tests")

# Import the OrbitRemit provider
try:
    from providers.orbitremit.exceptions import OrbitRemitError
    from providers.orbitremit.integration import OrbitRemitProvider
except ImportError:
    logger.error(
        "Failed to import OrbitRemit provider. Make sure you're running this from the project root."
    )
    logger.error("Try: PYTHONPATH=/path/to/project python apps/providers/orbitremit/tests.py")
    sys.exit(1)

# API endpoints for direct testing
BASE_URL = "https://www.orbitremit.com"
FEES_ENDPOINT = "/api/fees"

# Ensure the test output directory exists
TEST_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_output")
os.makedirs(TEST_OUTPUT_DIR, exist_ok=True)


def create_session():
    """Create a requests session with appropriate headers."""
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                "Version/18.3 Safari/605.1.15"
            ),
            "Accept": "*/*",
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
    )
    return session


def test_fees_api():
    """Test the OrbitRemit fees API endpoint directly."""
    logger.info("Testing OrbitRemit fees API: %s%s", BASE_URL, FEES_ENDPOINT)

    session = create_session()
    params = {
        "send": "AUD",
        "payout": "PHP",
        "amount": "200000.00",
        "type": "bank_account",
    }

    try:
        resp = session.get(BASE_URL + FEES_ENDPOINT, params=params, timeout=15)
        resp.raise_for_status()

        # Log the response
        data = resp.json()
        logger.info("API response: %s", json.dumps(data, indent=2))

        # Save the response to a file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"fees_response_{timestamp}.json"
        filepath = os.path.join(TEST_OUTPUT_DIR, filename)

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        logger.info("Response saved to %s", filepath)

        # Check if the response has the expected format
        if data.get("status") == "success" and "data" in data:
            fee_data = data["data"]
            fee = fee_data.get("fee")
            logger.info("✅ Fee: %s", fee)
            return True, data
        else:
            logger.error("❌ Unexpected response format: %s", data)
            return False, data

    except requests.exceptions.RequestException as e:
        logger.error("❌ Request failed: %s", e)
        return False, str(e)


def run_api_tests():
    """Run direct API tests against OrbitRemit."""
    logger.info("\n=========== RUNNING API TESTS ===========")

    success, data = test_fees_api()

    if success:
        logger.info("✅ API tests passed")
    else:
        logger.error("❌ API tests failed")

    return success


def test_factory():
    """Test the OrbitRemit provider through the factory."""
    logger.info("\n=========== RUNNING FACTORY TESTS ===========")

    try:
        # Import the provider factory
        from providers.factory import ProviderFactory

        # Get the OrbitRemit provider from the factory
        provider = ProviderFactory.get_provider("orbitremit")

        if provider is None:
            logger.error("❌ Failed to get OrbitRemit provider from factory")
            return False

        logger.info("Provider type: %s", type(provider))

        # Test getting fee info
        logger.info("\nTesting factory get_fee_info with AUD→PHP")

        result = provider.get_fee_info(
            send_currency="AUD",
            payout_currency="PHP",
            send_amount=Decimal("200000"),
            recipient_type="bank_account",
        )

        logger.info("Fee info result: %s", result)

        if result["success"] and result["fee"] is not None:
            logger.info("✅ Successful fee for AUD→PHP: %s", result["fee"])
            return True
        else:
            logger.error("❌ Failed to get fee for AUD→PHP: %s", result.get("error_message"))
            return False

    except ImportError:
        logger.warning("⚠️ Provider factory not found, skipping factory test")
        return None
    except Exception as e:
        logger.error("❌ Factory test error: %s", e)
        return False


def print_result(result):
    """Print a fee or quote result in a formatted way."""
    if result["success"]:
        if "fee" in result and result["fee"] is not None:
            logger.info(
                "✅ Fee Info Success: %s %s → Fee: %s",
                result["send_amount"],
                result["send_currency"],
                result["fee"],
            )
    else:
        logger.error("❌ Fee/Quote Failed: %s", result.get("error_message"))


def test_fee_info():
    """Test the get_fee_info method of the OrbitRemit provider."""
    logger.info("\n=========== RUNNING FEE INFO TESTS ===========")

    provider = OrbitRemitProvider()

    # List of test cases
    test_cases = [
        {
            "send_currency": "AUD",
            "payout_currency": "PHP",
            "send_amount": Decimal("200000"),
        },
        {
            "send_currency": "NZD",
            "payout_currency": "INR",
            "send_amount": Decimal("1000"),
        },
        {
            "send_currency": "GBP",
            "payout_currency": "PKR",
            "send_amount": Decimal("500"),
        },
        {
            "send_currency": "EUR",
            "payout_currency": "BDT",
            "send_amount": Decimal("1500"),
        },
        {
            "send_currency": "CAD",
            "payout_currency": "LKR",
            "send_amount": Decimal("750"),
        },
        {
            "send_currency": "USD",
            "payout_currency": "VND",
            "send_amount": Decimal("2000"),
        },
    ]

    success_count = 0

    for i, test_case in enumerate(test_cases, 1):
        logger.info(
            "\nTest %d/%d: Converting %s %s to %s",
            i,
            len(test_cases),
            test_case["send_amount"],
            test_case["send_currency"],
            test_case["payout_currency"],
        )

        result = provider.get_fee_info(**test_case)
        print_result(result)

        if result["success"]:
            success_count += 1

    logger.info("\nFee Info Tests: %d/%d successful", success_count, len(test_cases))
    return success_count == len(test_cases)


def test_quotes():
    """Test the get_quote method of the OrbitRemit provider."""
    logger.info("\n=========== RUNNING QUOTE TESTS ===========")

    provider = OrbitRemitProvider()

    # List of test cases
    test_cases = [
        {
            "amount": Decimal("200000"),
            "source_currency": "AUD",
            "target_currency": "PHP",
        },
        {"amount": Decimal("1000"), "source_currency": "NZD", "target_currency": "INR"},
        {"amount": Decimal("500"), "source_currency": "GBP", "target_currency": "PKR"},
        {"amount": Decimal("1500"), "source_currency": "EUR", "target_currency": "BDT"},
        {"amount": Decimal("750"), "source_currency": "CAD", "target_currency": "LKR"},
        {"amount": Decimal("2000"), "source_currency": "USD", "target_currency": "VND"},
    ]

    success_count = 0

    for i, test_case in enumerate(test_cases, 1):
        logger.info(
            "\nTest %d/%d: Converting %s %s to %s",
            i,
            len(test_cases),
            test_case["amount"],
            test_case["source_currency"],
            test_case["target_currency"],
        )

        result = provider.get_quote(**test_case)

        if result["success"]:
            logger.info(
                "✅ Quote Success: %s %s",
                test_case["amount"],
                test_case["source_currency"],
            )
            logger.info("   Fee: %s", result.get("fee"))
            success_count += 1
        else:
            logger.error("❌ Quote Failed: %s", result.get("error_message"))

    logger.info("\nQuote Tests: %d/%d successful", success_count, len(test_cases))
    return success_count == len(test_cases)


def test_error_handling():
    """Test error handling in the OrbitRemit provider."""
    logger.info("\n=========== RUNNING ERROR HANDLING TESTS ===========")

    provider = OrbitRemitProvider()

    # Define error test cases
    error_tests = [
        {
            "name": "Invalid Source Currency",
            "params": {
                "send_currency": "XYZ",  # Invalid source currency
                "payout_currency": "PHP",
                "send_amount": Decimal("1000"),
            },
            "expected_error": "Invalid source currency",
        },
        {
            "name": "Invalid Target Currency",
            "params": {
                "send_currency": "AUD",
                "payout_currency": "XYZ",  # Invalid target currency
                "send_amount": Decimal("1000"),
            },
            "expected_error": "Unsupported corridor",
        },
        {
            "name": "Empty Source Currency",
            "params": {
                "send_currency": "",  # Empty source currency
                "payout_currency": "PHP",
                "send_amount": Decimal("1000"),
            },
            "expected_error": "Send currency cannot be empty",
        },
        {
            "name": "Empty Target Currency",
            "params": {
                "send_currency": "AUD",
                "payout_currency": "",  # Empty target currency
                "send_amount": Decimal("1000"),
            },
            "expected_error": "Payout currency cannot be empty",
        },
        {
            "name": "Negative Amount",
            "params": {
                "send_currency": "AUD",
                "payout_currency": "PHP",
                "send_amount": Decimal("-1000"),  # Negative amount
            },
            "expected_error": "Amount must be positive",
        },
    ]

    success_count = 0

    for i, test in enumerate(error_tests, 1):
        logger.info("\nError Test %d/%d: %s", i, len(error_tests), test["name"])

        result = provider.get_fee_info(**test["params"])

        if (
            not result["success"]
            and result.get("error_message")
            and test["expected_error"] in result["error_message"]
        ):
            logger.info("✅ Test passed: success=False")
            logger.info("   Error message: %s", result["error_message"])
            success_count += 1
        else:
            logger.error(
                "❌ Test failed: Expected error containing '%s', got: %s",
                test["expected_error"],
                result.get("error_message"),
            )

    logger.info("\nError Handling Tests: %d/%d successful", success_count, len(error_tests))
    return success_count == len(error_tests)


def main():
    """Main entry point for the test script."""
    parser = argparse.ArgumentParser(description="Test OrbitRemit integration")
    parser.add_argument("--api", action="store_true", help="Run API tests")
    parser.add_argument("--factory", action="store_true", help="Run factory tests")
    parser.add_argument("--fee", action="store_true", help="Run fee info tests")
    parser.add_argument("--quote", action="store_true", help="Run quote tests")
    parser.add_argument("--errors", action="store_true", help="Run error handling tests")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    args = parser.parse_args()

    # If no arguments are provided, show help
    if not any(vars(args).values()):
        parser.print_help()
        return 0

    # Track overall test status
    all_tests_passed = True

    # Run requested tests
    if args.api or args.all:
        api_success = run_api_tests()
        all_tests_passed = all_tests_passed and api_success

    if args.factory or args.all:
        factory_success = test_factory()
        if factory_success is not None:  # Only update if factory test ran
            all_tests_passed = all_tests_passed and factory_success

    if args.fee or args.all:
        fee_success = test_fee_info()
        all_tests_passed = all_tests_passed and fee_success

    if args.quote or args.all:
        quote_success = test_quotes()
        all_tests_passed = all_tests_passed and quote_success

    if args.errors or args.all:
        error_success = test_error_handling()
        all_tests_passed = all_tests_passed and error_success

    # Report overall status
    if not all_tests_passed:
        logger.error("\n❌ Some tests failed!")
        return 1
    else:
        logger.info("\n✅ All tests passed!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
