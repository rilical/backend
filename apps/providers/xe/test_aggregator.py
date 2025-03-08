#!/usr/bin/env python3
"""
Test script for XE Money Transfer Aggregator Provider.
This demonstrates using the XEAggregatorProvider for getting quotes directly via the API.
"""

import logging
import json
import sys
import argparse
import random
from decimal import Decimal
from datetime import datetime
from pprint import pprint
import unittest

from apps.providers.xe.integration import XEAggregatorProvider
from apps.providers.xe.currency_mapping import (
    XE_SUPPORTED_CORRIDORS, 
    XE_COMMON_SOURCE_CURRENCIES, 
    XE_COUNTRY_TO_CURRENCY
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("xe_aggregator_test")

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
    "timestamp"
]

def test_xe_aggregator(amount: Decimal, source_currency: str, target_country: str, user_country: str = "US"):
    """
    Test the XE Aggregator Provider with the specified amount, source currency, and target country.
    
    Args:
        amount: Amount to send
        source_currency: Source currency code (e.g., 'USD', 'GBP')
        target_country: ISO country code of the receiving country (e.g., 'IN', 'PH')
        user_country: Optional user country for testing different perspectives
    
    Returns:
        The aggregator response
    """
    logger.info(f"Testing XE Aggregator Provider: {source_currency} -> {target_country} for {amount}")
    
    with XEAggregatorProvider() as provider:
        result = provider.get_exchange_rate(
            send_amount=amount,
            send_currency=source_currency,
            receive_country=target_country,
            user_country=user_country
        )
        
        return result

def test_supported_corridors(sample_size=None):
    """
    Test supported corridors with a sample amount.
    
    Args:
        sample_size: Optional number of random corridors to test (None for all)
    
    Returns:
        List of test results
    """
    results = []
    
    # Use all corridors or a random sample
    test_corridors = XE_SUPPORTED_CORRIDORS
    if sample_size and sample_size < len(XE_SUPPORTED_CORRIDORS):
        test_corridors = random.sample(XE_SUPPORTED_CORRIDORS, sample_size)
    
    with XEAggregatorProvider() as provider:
        for source_currency, target_country in test_corridors:
            logger.info(f"Testing corridor: {source_currency} -> {target_country}")
            
            try:
                result = provider.get_exchange_rate(
                    send_amount=Decimal("100"),
                    send_currency=source_currency,
                    receive_country=target_country
                )
                
                # Add some context for reporting
                summary = {
                    "corridor": f"{source_currency} -> {target_country}",
                    "success": result.get("success", False),
                    "error_message": result.get("error_message"),
                }
                
                if result.get("success"):
                    summary.update({
                        "exchange_rate": result.get("exchange_rate"),
                        "fee": result.get("fee"),
                        "delivery_time_minutes": result.get("delivery_time_minutes"),
                        "delivery_method": result.get("delivery_method"),
                    })
                
                results.append(summary)
            except Exception as e:
                logger.error(f"Error testing {source_currency} -> {target_country}: {str(e)}")
                results.append({
                    "corridor": f"{source_currency} -> {target_country}",
                    "success": False,
                    "error_message": f"Exception: {str(e)}",
                })
    
    return results

def test_new_country(source_currency="USD", sample_size=3):
    """
    Test sending to countries not explicitly in our supported list.
    
    Args:
        source_currency: Source currency to use
        sample_size: How many random countries to test
    
    Returns:
        Test results
    """
    # Get countries not explicitly in our supported list
    known_target_countries = set(country for _, country in XE_SUPPORTED_CORRIDORS)
    all_countries = set(XE_COUNTRY_TO_CURRENCY.keys())
    new_countries = list(all_countries - known_target_countries)
    
    # Pick random countries to test
    test_countries = random.sample(new_countries, min(sample_size, len(new_countries)))
    
    results = []
    with XEAggregatorProvider() as provider:
        for country in test_countries:
            logger.info(f"Testing new country corridor: {source_currency} -> {country}")
            
            try:
                result = provider.get_exchange_rate(
                    send_amount=Decimal("100"),
                    send_currency=source_currency,
                    receive_country=country
                )
                
                summary = {
                    "corridor": f"{source_currency} -> {country}",
                    "currency": XE_COUNTRY_TO_CURRENCY.get(country, "Unknown"),
                    "success": result.get("success", False),
                    "error_message": result.get("error_message"),
                }
                
                if result.get("success"):
                    summary.update({
                        "exchange_rate": result.get("exchange_rate"),
                        "fee": result.get("fee"),
                        "delivery_time_minutes": result.get("delivery_time_minutes"),
                    })
                
                results.append(summary)
            except Exception as e:
                logger.error(f"Error testing {source_currency} -> {country}: {str(e)}")
                results.append({
                    "corridor": f"{source_currency} -> {country}",
                    "success": False,
                    "error_message": f"Exception: {str(e)}",
                })
    
    return results

def test_currency_country_mapping():
    """
    Verify that our currency country mappings work by testing corridor support.
    
    Returns:
        Test results showing whether mappings work correctly
    """
    results = []
    
    # Test known corridors
    with XEAggregatorProvider() as provider:
        for source_currency, target_country in random.sample(XE_SUPPORTED_CORRIDORS, 3):
            is_supported = provider.is_corridor_supported(source_currency, target_country)
            
            results.append({
                "corridor": f"{source_currency} -> {target_country}",
                "type": "known",
                "is_supported": is_supported,
                "expected": True
            })
    
    # Test some random combinations
    random_source = random.sample(XE_COMMON_SOURCE_CURRENCIES, 2)
    random_target = random.sample(list(XE_COUNTRY_TO_CURRENCY.keys()), 3)
    
    with XEAggregatorProvider() as provider:
        for source in random_source:
            for target in random_target:
                is_supported = provider.is_corridor_supported(source, target)
                
                results.append({
                    "corridor": f"{source} -> {target}",
                    "type": "random",
                    "is_supported": is_supported,
                    "expected": True if source in XE_COMMON_SOURCE_CURRENCIES else "Unknown"
                })
    
    return results

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

def test_aggregator_format():
    """
    Test that the XE implementation returns responses in the proper aggregator format.
    
    Returns:
        Test results focusing on format validation
    """
    results = []
    
    # Test a successful corridor
    with XEAggregatorProvider() as provider:
        # 1. Test a successful case
        success_result = provider.get_exchange_rate(
            send_amount=Decimal("100"),
            send_currency="USD",
            receive_country="DE"
        )
        is_valid, missing = verify_aggregator_format(success_result)
        results.append({
            "test_case": "Success case (USD -> DE)",
            "valid_format": is_valid,
            "missing_fields": missing,
            "fields_present": list(success_result.keys()) if success_result else [],
            "success": success_result.get("success", False) if success_result else False
        })
        
        # 2. Test an invalid corridor (should return success=false)
        fail_result = provider.get_exchange_rate(
            send_amount=Decimal("100"),
            send_currency="XYZ",  # Invalid currency
            receive_country="DE"
        )
        is_valid, missing = verify_aggregator_format(fail_result)
        results.append({
            "test_case": "Failure case (invalid currency)",
            "valid_format": is_valid,
            "missing_fields": missing,
            "fields_present": list(fail_result.keys()) if fail_result else [],
            "success": fail_result.get("success", False) if fail_result else False
        })
        
        # 3. Test invalid amount (should return success=false)
        fail_amount_result = provider.get_exchange_rate(
            send_amount=Decimal("-100"),  # Negative amount
            send_currency="USD",
            receive_country="DE"
        )
        is_valid, missing = verify_aggregator_format(fail_amount_result)
        results.append({
            "test_case": "Failure case (negative amount)",
            "valid_format": is_valid,
            "missing_fields": missing,
            "fields_present": list(fail_amount_result.keys()) if fail_amount_result else [],
            "success": fail_amount_result.get("success", False) if fail_amount_result else False
        })
    
    return results

def test_error_handling():
    """
    Test that the XE implementation correctly handles various errors.
    
    Returns:
        Test results focusing on error handling
    """
    results = []
    
    with XEAggregatorProvider() as provider:
        # 1. Test missing parameters
        missing_param_result = provider.get_exchange_rate(
            send_amount=Decimal("100"),
            send_currency="USD", 
            receive_country=None  # Missing required parameter
        )
        results.append({
            "test_case": "Missing required param",
            "valid_format": missing_param_result.get("success") is False,
            "error_message": missing_param_result.get("error_message", "No error message"),
            "fields_present": list(missing_param_result.keys()) if missing_param_result else []
        })
        
        # 2. Test zero amount
        zero_amount_result = provider.get_exchange_rate(
            send_amount=Decimal("0"),
            send_currency="USD",
            receive_country="DE"
        )
        results.append({
            "test_case": "Zero amount",
            "valid_format": zero_amount_result.get("success") is False,
            "error_message": zero_amount_result.get("error_message", "No error message"),
            "fields_present": list(zero_amount_result.keys()) if zero_amount_result else []
        })

    return results

class TestXEAggregatorFormat(unittest.TestCase):
    """Unit tests for the XE Aggregator format validation."""
    
    def setUp(self):
        self.provider = XEAggregatorProvider()
    
    def tearDown(self):
        self.provider.close()
    
    def test_success_response_format(self):
        """Test that successful responses have all required fields."""
        result = self.provider.get_exchange_rate(
            send_amount=Decimal("100"),
            send_currency="USD",
            receive_country="DE"
        )
        
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
        # Test with invalid currency code
        result = self.provider.get_exchange_rate(
            send_amount=Decimal("100"),
            send_currency="XYZ",  # Invalid currency
            receive_country="DE"
        )
        
        # Check for required fields in error case
        for field in ["provider_id", "success", "error_message"]:
            self.assertIn(field, result, f"Missing required field: {field}")
        
        # Check error case specific validations
        self.assertFalse(result["success"], "Expected success=False")
        self.assertIsNotNone(result["error_message"], "Error message should be provided")
        self.assertIsNotNone(result["provider_id"], "Provider ID should be present")
        self.assertEqual(result["provider_id"], "XE", "Provider ID should be 'XE'")
    
    def test_negative_amount(self):
        """Test handling of negative amounts."""
        result = self.provider.get_exchange_rate(
            send_amount=Decimal("-100"),  # Negative amount
            send_currency="USD",
            receive_country="DE"
        )
        
        self.assertFalse(result["success"], "Negative amount should result in success=False")
        self.assertIsNotNone(result["error_message"], "Error message should be provided")
        self.assertTrue("amount" in result["error_message"].lower(), "Error should mention amount issue")

def main():
    """Main function to run XE Aggregator tests."""
    parser = argparse.ArgumentParser(description="Test XE Aggregator Provider")
    parser.add_argument("--amount", type=float, default=100.0, help="Amount to send")
    parser.add_argument("--source-currency", type=str, default="USD", help="Source currency code")
    parser.add_argument("--target-country", type=str, default="IN", help="Target country code")
    parser.add_argument("--user-country", type=str, default="US", help="User's country code")
    parser.add_argument("--test-all", action="store_true", help="Test all supported corridors")
    parser.add_argument("--sample", type=int, default=5, help="Number of random corridors to test")
    parser.add_argument("--test-new", action="store_true", help="Test new/untested countries")
    parser.add_argument("--test-mapping", action="store_true", help="Test currency/country mapping")
    parser.add_argument("--test-format", action="store_true", help="Test aggregator format compliance")
    parser.add_argument("--test-errors", action="store_true", help="Test error handling")
    parser.add_argument("--unittest", action="store_true", help="Run unit tests")
    parser.add_argument("--output", type=str, help="Output file for results (JSON)")
    
    args = parser.parse_args()
    
    if args.unittest:
        # Run unittest test cases
        unittest.main(argv=['first-arg-is-ignored'])
        return
        
    if args.test_format:
        logger.info("Testing aggregator format compliance...")
        results = test_aggregator_format()
        
        if args.output:
            with open(args.output, "w") as f:
                json.dump(results, f, indent=2)
        else:
            print("\nAggregator Format Test Results:")
            for result in results:
                valid = "✅" if result.get("valid_format") else "❌"
                success = "Success" if result.get("success") else "Failure"
                missing = f", Missing: {result.get('missing_fields')}" if result.get("missing_fields") else ""
                print(f"{valid} {result['test_case']} ({success}){missing}")
                print(f"   Fields present: {result.get('fields_present')}")
                print()
                
    elif args.test_errors:
        logger.info("Testing error handling...")
        results = test_error_handling()
        
        if args.output:
            with open(args.output, "w") as f:
                json.dump(results, f, indent=2)
        else:
            print("\nError Handling Test Results:")
            for result in results:
                valid = "✅" if result.get("valid_format") else "❌"
                print(f"{valid} {result['test_case']}")
                print(f"   Error message: {result.get('error_message')}")
                print(f"   Fields present: {result.get('fields_present')}")
                print()
                
    elif args.test_all:
        logger.info(f"Testing {args.sample} random supported corridors...")
        results = test_supported_corridors(sample_size=args.sample)
        
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
                error = f": {result.get('error_message')}" if not result.get("success") else ""
                rate = f" (Rate: {result.get('exchange_rate')})" if result.get("success") else ""
                print(f"{status} {result['corridor']}{rate}{error}")
    
    elif args.test_new:
        logger.info(f"Testing {args.sample} new countries with {args.source_currency}...")
        results = test_new_country(args.source_currency, args.sample)
        
        # Print summary
        success_count = sum(1 for r in results if r.get("success"))
        logger.info(f"Results: {success_count} successful out of {len(results)} corridors")
        
        # Output details
        if args.output:
            with open(args.output, "w") as f:
                json.dump(results, f, indent=2)
        else:
            print("\nNew country test results:")
            for result in results:
                status = "✅" if result.get("success") else "❌"
                error = f": {result.get('error_message')}" if not result.get("success") else ""
                currency = f" ({result.get('currency')})"
                print(f"{status} {result['corridor']}{currency}{error}")
    
    elif args.test_mapping:
        logger.info("Testing currency/country mapping...")
        results = test_currency_country_mapping()
        
        if args.output:
            with open(args.output, "w") as f:
                json.dump(results, f, indent=2)
        else:
            print("\nCurrency/Country mapping test results:")
            for result in results:
                status = "✅" if result.get("is_supported") else "❌"
                expected = f" (Expected: {result.get('expected')})"
                print(f"{status} {result['corridor']} - Type: {result['type']}{expected}")
                
    else:
        # Test single corridor
        result = test_xe_aggregator(
            amount=Decimal(str(args.amount)),
            source_currency=args.source_currency,
            target_country=args.target_country,
            user_country=args.user_country
        )
        
        print("\nXE Aggregator Provider Result:")
        pprint(result)
        
        # Check if the result is in the proper aggregator format
        is_valid_format, missing_fields = verify_aggregator_format(result)
        print(f"\nAggregator Format Valid: {is_valid_format}")
        if not is_valid_format:
            print(f"Missing/Invalid Fields: {missing_fields}")
        
        if args.output:
            with open(args.output, "w") as f:
                # Convert to dict for JSON serialization
                serializable_result = {k: str(v) if isinstance(v, Decimal) else v for k, v in result.items()}
                json.dump(serializable_result, f, indent=2)

if __name__ == "__main__":
    main() 