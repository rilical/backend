#!/usr/bin/env python3
"""
Test script for Xoom Aggregator Provider.
This file tests the XoomAggregatorProvider which is the aggregator-ready version
of the Xoom integration that returns standardized responses with no fallbacks.
"""

import argparse
import json
import logging
import unittest
from decimal import Decimal
from pprint import pprint

from apps.providers.xoom.aggregator import XoomAggregatorProvider

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("xoom_aggregator_test")

# Required fields in the aggregator-ready format
REQUIRED_AGGREGATOR_FIELDS = [
    "provider_id",
    "success",
    "error_message",
    "send_amount",
    "source_currency",
    "destination_amount",
    "destination_currency",
    "exchange_rate",
    "fee",
    "payment_method",
    "delivery_method",
    "delivery_time_minutes",
    "timestamp",
]

# Common Xoom corridors for testing
TEST_CORRIDORS = [
    {"source_currency": "USD", "target_country": "MX", "amount": 200},
    {"source_currency": "USD", "target_country": "PH", "amount": 200},
    {"source_currency": "USD", "target_country": "IN", "amount": 200},
    {"source_currency": "USD", "target_country": "CO", "amount": 200},
]


def test_xoom_aggregator(amount: Decimal, source_currency: str, target_country: str):
    """
    Test the Xoom Aggregator Provider with the specified amount, source currency, and target country.

    Args:
        amount: Amount to send
        source_currency: Source currency code (e.g., 'USD')
        target_country: ISO country code of the receiving country (e.g., 'MX')

    Returns:
        The aggregator response
    """
    logger.info(
        f"Testing Xoom Aggregator Provider: {source_currency} -> {target_country} for {amount}"
    )

    with XoomAggregatorProvider() as provider:
        result = provider.get_exchange_rate(
            send_amount=amount,
            send_currency=source_currency,
            receive_country=target_country,
        )

        return result


def verify_aggregator_format(result):
    """
    Verify that a result follows the aggregator-ready format.

    Args:
        result: The result to verify

    Returns:
        Tuple of (is_valid, missing_fields)
    """
    if not result:
        return False, ["No result returned"]

    missing_fields = []
    for field in REQUIRED_AGGREGATOR_FIELDS:
        if field not in result:
            missing_fields.append(field)

    # Additional validations for success cases
    if result.get("success", False):
        # Validate types and values for successful responses
        if result.get("exchange_rate", 0) <= 0:
            missing_fields.append("valid exchange_rate")
        if not isinstance(result.get("send_amount"), (int, float, Decimal)):
            missing_fields.append("valid send_amount")
        if not isinstance(result.get("destination_amount"), (int, float, Decimal)):
            missing_fields.append("valid destination_amount")
        if result.get("destination_amount", 0) <= 0:
            missing_fields.append("positive destination_amount")
    else:
        # For failure cases, ensure there's an error message
        if not result.get("error_message"):
            missing_fields.append("error_message for failed response")

    return len(missing_fields) == 0, missing_fields


def test_all_corridors():
    """
    Test all corridors in the TEST_CORRIDORS list to ensure they work correctly.

    Returns:
        List of test results
    """
    results = []

    with XoomAggregatorProvider() as provider:
        for corridor in TEST_CORRIDORS:
            logger.info(
                f"Testing corridor: {corridor['source_currency']} -> {corridor['target_country']}"
            )

            try:
                result = provider.get_exchange_rate(
                    send_amount=Decimal(str(corridor["amount"])),
                    send_currency=corridor["source_currency"],
                    receive_country=corridor["target_country"],
                )

                is_valid, missing = verify_aggregator_format(result)

                # Add some context for reporting
                summary = {
                    "corridor": f"{corridor['source_currency']} -> {corridor['target_country']}",
                    "success": result.get("success", False),
                    "valid_format": is_valid,
                    "missing_fields": missing,
                    "error_message": result.get("error_message"),
                }

                if result.get("success"):
                    summary.update(
                        {
                            "exchange_rate": result.get("exchange_rate"),
                            "fee": result.get("fee"),
                            "delivery_time_minutes": result.get("delivery_time_minutes"),
                        }
                    )

                results.append(summary)
            except Exception as e:
                logger.error(f"Error testing {corridor}: {str(e)}")
                results.append(
                    {
                        "corridor": f"{corridor['source_currency']} -> {corridor['target_country']}",
                        "success": False,
                        "error_message": f"Exception: {str(e)}",
                    }
                )

    return results


def test_error_handling():
    """Test how the provider handles error cases."""
    results = []

    with XoomAggregatorProvider() as provider:
        # Test with invalid country
        invalid_country_result = provider.get_exchange_rate(
            send_amount=Decimal("100"),
            send_currency="USD",
            receive_country="XX",  # Invalid country code
        )

        is_valid, missing = verify_aggregator_format(invalid_country_result)
        results.append(
            {
                "test_case": "Invalid country",
                "success": invalid_country_result.get("success", False),
                "valid_format": is_valid,
                "missing_fields": missing,
                "error_message": invalid_country_result.get("error_message"),
            }
        )

        # Test with invalid currency
        invalid_currency_result = provider.get_exchange_rate(
            send_amount=Decimal("100"),
            send_currency="XYZ",  # Invalid currency
            receive_country="MX",
        )

        is_valid, missing = verify_aggregator_format(invalid_currency_result)
        results.append(
            {
                "test_case": "Invalid currency",
                "success": invalid_currency_result.get("success", False),
                "valid_format": is_valid,
                "missing_fields": missing,
                "error_message": invalid_currency_result.get("error_message"),
            }
        )

        # Test with missing required parameter
        missing_param_result = provider.get_exchange_rate(
            send_amount=Decimal("100"),
            send_currency="USD",
            receive_country=None,  # Missing required param
        )

        is_valid, missing = verify_aggregator_format(missing_param_result)
        results.append(
            {
                "test_case": "Missing required param",
                "success": missing_param_result.get("success", False),
                "valid_format": is_valid,
                "missing_fields": missing,
                "error_message": missing_param_result.get("error_message"),
            }
        )

    return results


class TestXoomAggregatorFormat(unittest.TestCase):
    """Unit tests for the Xoom Aggregator format validation."""

    def setUp(self):
        self.provider = XoomAggregatorProvider()

    def tearDown(self):
        self.provider.close()

    def test_success_response_format(self):
        """Test that successful responses have all required fields."""
        result = self.provider.get_exchange_rate(
            send_amount=Decimal("100"), send_currency="USD", receive_country="MX"
        )

        # Skip the test if the API couldn't be reached
        if not result.get("success"):
            self.skipTest(f"API returned error: {result.get('error_message')}")

        # Check for required fields
        for field in REQUIRED_AGGREGATOR_FIELDS:
            self.assertIn(field, result, f"Missing required field: {field}")

        # Check success case specific validations
        self.assertTrue(result["success"], "Expected success=True")
        self.assertIsNone(result["error_message"], "Error message should be None on success")
        self.assertGreater(result["exchange_rate"], 0, "Exchange rate should be positive")
        self.assertGreater(result["destination_amount"], 0, "Destination amount should be positive")
        self.assertIn("raw_response", result, "Raw response should be included")

    def test_error_response_format(self):
        """Test that error responses have all required fields and appropriate error info."""
        # Test with invalid country code
        result = self.provider.get_exchange_rate(
            send_amount=Decimal("100"),
            send_currency="USD",
            receive_country="XX",  # Invalid country
        )

        # Check for required fields in error case
        for field in ["provider_id", "success", "error_message"]:
            self.assertIn(field, result, f"Missing required field: {field}")

        # Check error case specific validations
        self.assertFalse(result["success"], "Expected success=False")
        self.assertIsNotNone(result["error_message"], "Error message should be provided")
        self.assertIsNotNone(result["provider_id"], "Provider ID should be present")
        self.assertEqual(result["provider_id"], "Xoom", "Provider ID should be 'Xoom'")


def main():
    """Main entry point for the test script."""
    parser = argparse.ArgumentParser(description="Test Xoom Aggregator Provider")
    parser.add_argument("--amount", type=float, default=100.0, help="Amount to send")
    parser.add_argument("--source-currency", type=str, default="USD", help="Source currency code")
    parser.add_argument("--target-country", type=str, default="MX", help="Target country code")
    parser.add_argument("--test-all", action="store_true", help="Test all corridors")
    parser.add_argument("--test-errors", action="store_true", help="Test error handling")
    parser.add_argument("--unittest", action="store_true", help="Run unit tests")
    parser.add_argument("--output", type=str, help="Output file for results (JSON)")

    args = parser.parse_args()

    if args.unittest:
        # Run unittest test cases
        unittest.main(argv=["first-arg-is-ignored"])
        return

    if args.test_all:
        logger.info("Testing all corridors...")
        results = test_all_corridors()

        # Print summary
        success_count = sum(1 for r in results if r.get("success"))
        logger.info(f"Results: {success_count} successful out of {len(results)} corridors")

        # Output details
        if args.output:
            with open(args.output, "w") as f:
                json.dump(results, f, indent=2)
        else:
            print("\nSummary of results:")
            for result in results:
                status = "✅" if result.get("success") else "❌"
                format_status = "✅" if result.get("valid_format") else "❌"
                error = f": {result.get('error_message')}" if not result.get("success") else ""
                rate = f" (Rate: {result.get('exchange_rate')})" if result.get("success") else ""
                print(f"{status} {result['corridor']}{rate} - Format: {format_status}{error}")

    elif args.test_errors:
        logger.info("Testing error handling...")
        results = test_error_handling()

        if args.output:
            with open(args.output, "w") as f:
                json.dump(results, f, indent=2)
        else:
            print("\nError Handling Test Results:")
            for result in results:
                status = (
                    "✅" if not result.get("success") else "❌"
                )  # For error tests, we expect failure
                format_status = "✅" if result.get("valid_format") else "❌"
                print(f"{status} {result['test_case']} - Format: {format_status}")
                print(f"   Error message: {result.get('error_message')}")
                print(f"   Missing fields: {result.get('missing_fields', [])}")
                print()

    else:
        # Test single corridor
        result = test_xoom_aggregator(
            amount=Decimal(str(args.amount)),
            source_currency=args.source_currency,
            target_country=args.target_country,
        )

        print("\nXoom Aggregator Provider Result:")
        pprint(result)

        # Check if the result is in the proper aggregator format
        is_valid_format, missing_fields = verify_aggregator_format(result)
        print(f"\nAggregator Format Valid: {is_valid_format}")
        if not is_valid_format:
            print(f"Missing/Invalid Fields: {missing_fields}")

        if args.output:
            with open(args.output, "w") as f:
                # Convert Decimal objects for JSON serialization
                serializable_result = {
                    k: (str(v) if isinstance(v, Decimal) else v) for k, v in result.items()
                }
                json.dump(serializable_result, f, indent=2)


if __name__ == "__main__":
    main()
