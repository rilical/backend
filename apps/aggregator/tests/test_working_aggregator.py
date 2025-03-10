#!/usr/bin/env python
"""
Test script for manually testing providers.

This script directly calls each provider with its specific requirements.
"""

import os
import sys
import logging
import time
from decimal import Decimal
from tabulate import tabulate

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Import providers
from apps.providers.xe.integration import XEAggregatorProvider
from apps.providers.remitly.integration import RemitlyProvider
from apps.providers.ria.integration import RIAProvider

# Test parameters
TEST_PARAMS = {
    "corridor_name": "USD to INR (US to India)",
    "source_country": "US",
    "dest_country": "IN",
    "source_currency": "USD",
    "dest_currency": "INR",
    "amount": Decimal("1000.00")
}

def test_all_providers():
    """
    Test all providers with the test parameters.
    """
    results = []
    
    # Test XE provider
    try:
        print("\nTesting XE provider...")
        xe_provider = XEAggregatorProvider()
        
        # XE provider uses get_exchange_rate with specific parameter names
        xe_result = xe_provider.get_exchange_rate(
            send_amount=TEST_PARAMS["amount"],
            send_currency=TEST_PARAMS["source_currency"],
            receive_country=TEST_PARAMS["dest_country"]
        )
        
        # Add provider_id if not present
        if not xe_result.get("provider_id"):
            xe_result["provider_id"] = "XE"
        
        results.append(xe_result)
        
        if xe_result.get("success"):
            print(f"SUCCESS - Rate: {xe_result.get('exchange_rate')}, Fee: {xe_result.get('fee')}")
        else:
            print(f"FAILED - Error: {xe_result.get('error_message')}")
    except Exception as e:
        print(f"Error testing XE: {str(e)}")
        results.append({
            "provider_id": "XE",
            "success": False,
            "error_message": str(e)
        })
    
    # Test Remitly provider
    try:
        print("\nTesting Remitly provider...")
        remitly_provider = RemitlyProvider()
        
        # Remitly provider uses get_quote with specific parameter names
        remitly_result = remitly_provider.get_quote(
            amount=TEST_PARAMS["amount"],
            source_currency=TEST_PARAMS["source_currency"],
            dest_currency=TEST_PARAMS["dest_currency"],
            source_country=TEST_PARAMS["source_country"],
            dest_country=TEST_PARAMS["dest_country"]
        )
        
        # Add provider_id if not present
        if not remitly_result.get("provider_id"):
            remitly_result["provider_id"] = "Remitly"
        
        results.append(remitly_result)
        
        if remitly_result.get("success"):
            print(f"SUCCESS - Rate: {remitly_result.get('exchange_rate')}, Fee: {remitly_result.get('fee')}")
        else:
            print(f"FAILED - Error: {remitly_result.get('error_message')}")
    except Exception as e:
        print(f"Error testing Remitly: {str(e)}")
        results.append({
            "provider_id": "Remitly",
            "success": False,
            "error_message": str(e)
        })
    
    # Test RIA provider
    try:
        print("\nTesting RIA provider...")
        ria_provider = RIAProvider()
        
        # RIA provider uses get_quote with specific parameter names and additional parameters
        ria_result = ria_provider.get_quote(
            amount=TEST_PARAMS["amount"],
            source_currency=TEST_PARAMS["source_currency"],
            dest_currency=TEST_PARAMS["dest_currency"],
            source_country=TEST_PARAMS["source_country"],
            dest_country=TEST_PARAMS["dest_country"],
            payment_method="debitCard",
            delivery_method="bankDeposit"
        )
        
        # Add provider_id if not present
        if not ria_result.get("provider_id"):
            ria_result["provider_id"] = "RIA"
        
        results.append(ria_result)
        
        if ria_result.get("success"):
            print(f"SUCCESS - Rate: {ria_result.get('exchange_rate')}, Fee: {ria_result.get('fee')}")
        else:
            print(f"FAILED - Error: {ria_result.get('error_message')}")
    except Exception as e:
        print(f"Error testing RIA: {str(e)}")
        results.append({
            "provider_id": "RIA",
            "success": False,
            "error_message": str(e)
        })
    
    # Print a summary table
    print("\nTEST RESULTS SUMMARY")
    print("===================")
    
    table_data = []
    for result in results:
        provider_id = result.get("provider_id", "Unknown")
        success = result.get("success", False)
        
        if success:
            table_data.append([
                provider_id,
                "✓",
                result.get("exchange_rate", "N/A"),
                result.get("fee", "N/A"),
                result.get("destination_amount", "N/A"),
                result.get("delivery_time_minutes", "N/A")
            ])
        else:
            table_data.append([
                provider_id,
                "✗",
                "N/A",
                "N/A",
                "N/A",
                result.get("error_message", "Unknown error")
            ])
    
    headers = ["Provider", "Success", "Rate", "Fee", "Recipient Gets", "Delivery Time/Error"]
    print(tabulate(table_data, headers=headers, tablefmt="pipe"))

if __name__ == "__main__":
    test_all_providers() 