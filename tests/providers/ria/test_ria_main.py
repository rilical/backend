#!/usr/bin/env python3
"""
RIA Provider Integration Tests

This script tests the RIA provider to confirm it's returning real data from the API
with no mock/fallback data. If an API call fails or a corridor is unsupported,
it should properly return a standardized response with success=False.
"""

import sys
import os
import logging
import time
import json
from decimal import Decimal
from typing import Dict, List, Any, Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ria_tests")

# Ensure we can import from the parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

# Import the RIA provider
from apps.providers.ria.integration import RIAProvider

# Define test corridors - mix of expected working and failing ones
TEST_CORRIDORS = [
    # Expected to work
    {"name": "USD->MXN", "send_amount": 200, "send_country": "US", "send_currency": "USD", "dest_country": "MX", "dest_currency": "MXN", "expected_success": True},
    {"name": "USD->INR", "send_amount": 500, "send_country": "US", "send_currency": "USD", "dest_country": "IN", "dest_currency": "INR", "expected_success": True},
    {"name": "USD->PHP", "send_amount": 300, "send_country": "US", "send_currency": "USD", "dest_country": "PH", "dest_currency": "PHP", "expected_success": True},
    
    # Lower bounds testing
    {"name": "USD->MXN (small)", "send_amount": 10, "send_country": "US", "send_currency": "USD", "dest_country": "MX", "dest_currency": "MXN", "expected_success": True},
    
    # Possibly unsupported
    {"name": "USD->ZAR", "send_amount": 100, "send_country": "US", "send_currency": "USD", "dest_country": "ZA", "dest_currency": "ZAR", "expected_success": None},  # May or may not work
    {"name": "CAD->KES", "send_amount": 100, "send_country": "CA", "send_currency": "CAD", "dest_country": "KE", "dest_currency": "KES", "expected_success": None},  # May or may not work
    
    # Should definitely fail
    {"name": "JPY->BRL", "send_amount": 100, "send_country": "JP", "send_currency": "JPY", "dest_country": "BR", "dest_currency": "BRL", "expected_success": False},
    {"name": "USD->XXX (invalid)", "send_amount": 100, "send_country": "US", "send_currency": "USD", "dest_country": "XX", "dest_currency": "XXX", "expected_success": False},
]

def format_result(corridor: Dict[str, Any], result: Dict[str, Any]) -> str:
    """Format the test result for display"""
    if result["success"]:
        return (
            f"✅ {corridor['name']}: {corridor['send_amount']} {corridor['send_currency']} → "
            f"{result['destination_amount']:.2f} {result['destination_currency']} | "
            f"Rate: {result['exchange_rate']:.4f} | Fee: {result['fee']:.2f} {corridor['send_currency']}"
        )
    else:
        return f"❌ {corridor['name']}: Failed - {result['error_message']}"

def test_get_quote() -> None:
    """Test the get_quote method with various corridors"""
    logger.info("Testing get_quote() method with various corridors...")
    
    with RIAProvider() as provider:
        for corridor in TEST_CORRIDORS:
            start_time = time.time()
            result = provider.get_quote(
                amount=Decimal(str(corridor["send_amount"])),
                source_currency=corridor["send_currency"],
                dest_currency=corridor["dest_currency"],
                source_country=corridor["send_country"],
                dest_country=corridor["dest_country"],
            )
            elapsed = time.time() - start_time
            
            formatted_result = format_result(corridor, result)
            logger.info(f"{formatted_result} (took {elapsed:.2f}s)")
            
            # Verify expected results if specified
            if corridor["expected_success"] is not None:
                assert result["success"] == corridor["expected_success"], \
                    f"Expected success={corridor['expected_success']} but got {result['success']}"
            
            # For successful calls, verify key fields
            if result["success"]:
                assert result["exchange_rate"] > 0, "Exchange rate should be positive"
                assert result["destination_amount"] > 0, "Destination amount should be positive"
                assert "destination_currency" in result, "Destination currency should be present"
                assert result["fee"] is not None, "Fee should be present (even if 0)"
                
                # Check for delivery methods
                if "available_delivery_methods" in result:
                    logger.info(f"  Available delivery methods for {corridor['name']}:")
                    for method in result["available_delivery_methods"]:
                        logger.info(f"  - {method['method_name']} ({method['standardized_name']}): " + 
                                  (f"Rate: {method.get('exchange_rate', 'N/A')}" if 'exchange_rate' in method else "No rate"))
                
                # Check for payment methods
                if "available_payment_methods" in result:
                    logger.info(f"  Available payment methods for {corridor['name']}:")
                    for method in result["available_payment_methods"]:
                        logger.info(f"  - {method['method_name']} ({method['standardized_name']})")
            else:
                assert result["error_message"], "Failed result should have an error message"

def test_get_exchange_rate() -> None:
    """Test the legacy get_exchange_rate method with expected working corridors"""
    logger.info("Testing get_exchange_rate() method with working corridors...")
    
    working_corridors = [c for c in TEST_CORRIDORS if c["expected_success"] is True]
    
    with RIAProvider() as provider:
        for corridor in working_corridors:
            start_time = time.time()
            result = provider.get_exchange_rate(
                send_amount=Decimal(str(corridor["send_amount"])),
                send_country=corridor["send_country"],
                send_currency=corridor["send_currency"],
                receive_currency=corridor["dest_currency"],
                dest_country=corridor["dest_country"],
            )
            elapsed = time.time() - start_time
            
            formatted_result = format_result(corridor, result)
            logger.info(f"{formatted_result} (took {elapsed:.2f}s)")
            
            # Verify result
            assert result["success"] == True, f"Expected success=True but got {result['success']}"
            assert result["exchange_rate"] > 0, "Exchange rate should be positive"
            assert result["destination_amount"] > 0, "Destination amount should be positive"

def test_provider_details() -> None:
    """Test the provider's capability methods"""
    logger.info("Testing provider details and capabilities...")
    
    with RIAProvider() as provider:
        # Describe the provider
        logger.info(f"Provider name: {provider.name}")
        logger.info(f"Default payment method: {provider.DEFAULT_PAYMENT_METHOD}")
        logger.info(f"Default delivery method: {provider.DEFAULT_DELIVERY_METHOD}")
        
        # List the delivery method mappings
        logger.info("Delivery method mappings:")
        for ria_code, standard_name in provider.DELIVERY_METHOD_MAP.items():
            logger.info(f"  - {ria_code} → {standard_name}")
            
        # List the payment method mappings
        logger.info("Payment method mappings:")
        for ria_code, standard_name in provider.PAYMENT_METHOD_MAP.items():
            logger.info(f"  - {ria_code} → {standard_name}")

def test_delivery_methods() -> None:
    """Test delivery methods for specific corridors"""
    logger.info("Testing delivery methods for specific corridors...")
    
    # Test corridors known to have multiple delivery methods
    delivery_test_corridors = [
        {"name": "USD->INR", "send_amount": 200, "send_country": "US", "send_currency": "USD", "dest_country": "IN", "dest_currency": "INR"},
        {"name": "USD->PH", "send_amount": 200, "send_country": "US", "send_currency": "USD", "dest_country": "PH", "dest_currency": "PHP"},
        {"name": "USD->MX", "send_amount": 200, "send_country": "US", "send_currency": "USD", "dest_country": "MX", "dest_currency": "MXN"},
    ]
    
    with RIAProvider() as provider:
        for corridor in delivery_test_corridors:
            logger.info(f"Testing delivery methods for {corridor['name']}...")
            
            # Get quote with default delivery method, enable debug mode
            result = provider.get_quote(
                amount=Decimal(str(corridor["send_amount"])),
                source_currency=corridor["send_currency"],
                dest_currency=corridor["dest_currency"],
                source_country=corridor["send_country"],
                dest_country=corridor["dest_country"],
                debug_mode=True  # Enable debug mode to capture raw response
            )
            
            if result["success"] and "available_delivery_methods" in result:
                methods = result["available_delivery_methods"]
                logger.info(f"Found {len(methods)} delivery methods for {corridor['name']}")
                
                if methods:
                    # Print details of each delivery method
                    for idx, method in enumerate(methods, 1):
                        rate_info = f"Rate: {method.get('exchange_rate', 'N/A')}" if "exchange_rate" in method else "No rate info"
                        best_rate = "(BEST RATE)" if method.get("is_best_rate") else ""
                        logger.info(f"  {idx}. {method['method_name']} ({method['method_code']}) → {method['standardized_name']} | {rate_info} {best_rate}")
                    
                    # Now test each delivery method specifically
                    if len(methods) > 1:
                        # Test the first alternative delivery method
                        alt_method = methods[1]["method_code"] 
                        logger.info(f"Testing specific delivery method: {alt_method}")
                        
                        alt_result = provider.get_quote(
                            amount=Decimal(str(corridor["send_amount"])),
                            source_currency=corridor["send_currency"],
                            dest_currency=corridor["dest_currency"],
                            source_country=corridor["send_country"],
                            dest_country=corridor["dest_country"],
                            delivery_method=alt_method
                        )
                        
                        if alt_result["success"]:
                            logger.info(f"  ✅ Quote with {alt_method}: Rate {alt_result['exchange_rate']}, Amount {alt_result['destination_amount']}")
                        else:
                            logger.info(f"  ❌ Failed to get quote with {alt_method}: {alt_result['error_message']}")
            else:
                logger.warning(f"No delivery methods found for {corridor['name']} or request failed")
                
                # Try with a different payment method to see if that reveals delivery methods
                logger.info(f"Trying with different payment method (BankAccount) for {corridor['name']}...")
                alt_result = provider.get_quote(
                    amount=Decimal(str(corridor["send_amount"])),
                    source_currency=corridor["send_currency"],
                    dest_currency=corridor["dest_currency"],
                    source_country=corridor["send_country"],
                    dest_country=corridor["dest_country"],
                    payment_method="BankAccount",
                    debug_mode=True
                )
                
                if alt_result["success"] and "available_delivery_methods" in alt_result:
                    methods = alt_result["available_delivery_methods"]
                    logger.info(f"Found {len(methods)} delivery methods for {corridor['name']} with BankAccount payment")
                    for idx, method in enumerate(methods, 1):
                        logger.info(f"  {idx}. {method['method_name']} ({method['method_code']}) → {method['standardized_name']}")
                else:
                    logger.warning(f"Still no delivery methods found with BankAccount payment")

def test_error_handling() -> None:
    """Test error handling with invalid inputs"""
    logger.info("Testing error handling...")
    
    with RIAProvider() as provider:
        # Test with invalid send country
        result = provider.get_quote(
            amount=Decimal("100"),
            source_currency="USD",
            dest_currency="MXN",
            source_country="ZZ",  # Invalid country code
            dest_country="MX",
        )
        logger.info(f"Invalid source country: success={result['success']}, error={result['error_message']}")
        assert result["success"] is False, "Should fail with invalid source country"
        
        # Test with negative amount
        result = provider.get_quote(
            amount=Decimal("-100"),
            source_currency="USD",
            dest_currency="MXN",
            source_country="US",
            dest_country="MX",
        )
        logger.info(f"Negative amount: success={result['success']}, error={result['error_message']}")
        assert result["success"] is False, "Should fail with negative amount"

def main() -> None:
    """Run all tests"""
    logger.info("Starting RIA provider tests...")
    
    # Run individual test functions
    test_get_quote()
    logger.info("-" * 40)
    
    test_get_exchange_rate()
    logger.info("-" * 40)
    
    test_provider_details()
    logger.info("-" * 40)
    
    test_delivery_methods()
    logger.info("-" * 40)
    
    test_error_handling()
    logger.info("-" * 40)
    
    logger.info("All tests completed!")

if __name__ == "__main__":
    main()