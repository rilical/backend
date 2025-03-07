#!/usr/bin/env python3
"""
Test script for the aggregator-ready TransferGo provider implementation.
This script tests the TransferGo provider with live APIs to verify it works correctly.
"""

import sys
import logging
import argparse
from decimal import Decimal
import json
from datetime import datetime
import os
import random

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add the parent directory to the path so we can import the provider
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../.."))
sys.path.insert(0, project_root)

# Import the provider
from apps.providers.transfergo.aggregator_integration import TransferGoProvider
from apps.providers.transfergo.transfergo_mappings import (
    POPULAR_CORRIDORS,
    COUNTRY_CURRENCIES,
    get_supported_source_countries,
    get_supported_destination_countries,
    CASH_PICKUP_COUNTRIES,
    MOBILE_WALLET_COUNTRIES
)

def format_json(data):
    """Format JSON data for pretty printing"""
    return json.dumps(data, indent=2, sort_keys=True)

def test_corridor(provider, amount, source_country, source_currency, 
                 destination_country, destination_currency, 
                 payment_method=None, delivery_method=None):
    """Test a specific corridor with the provider"""
    logger = logging.getLogger("test_corridor")
    
    logger.info(f"Testing corridor: {source_currency} ({source_country}) → "
               f"{destination_currency} ({destination_country}) for {amount} {source_currency}")
    
    try:
        # Get a quote
        result = provider.get_quote(
            amount=Decimal(amount),
            source_currency=source_currency,
            destination_currency=destination_currency,
            source_country=source_country,
            destination_country=destination_country,
            payment_method=payment_method,
            delivery_method=delivery_method
        )
        
        # Check if the request was successful
        if result["success"]:
            logger.info(f"✅ SUCCESS: {amount} {source_currency} → "
                       f"{result['destination_amount']} {result['destination_currency']}")
            logger.info(f"Exchange rate: {result['exchange_rate']}")
            logger.info(f"Fee: {result['fee']}")
            
            # Check if delivery methods are available
            if "available_delivery_methods" in result:
                logger.info(f"Available delivery methods: {len(result['available_delivery_methods'])}")
                for method in result['available_delivery_methods']:
                    logger.info(f"  - {method['method_name']} ({method['standardized_name']})")
            
            # Check if payment methods are available
            if "available_payment_methods" in result:
                logger.info(f"Available payment methods: {len(result['available_payment_methods'])}")
                for method in result['available_payment_methods']:
                    logger.info(f"  - {method['method_name']} ({method['standardized_name']})")
            
            return True
        else:
            logger.error(f"❌ FAILED: {result['error_message']}")
            return False
            
    except Exception as e:
        logger.error(f"❌ ERROR: {str(e)}", exc_info=True)
        return False

def test_with_receive_amount(provider, receive_amount, source_country, source_currency, 
                           destination_country, destination_currency):
    """Test a specific corridor with a receive amount instead of send amount"""
    logger = logging.getLogger("test_receive_amount")
    
    logger.info(f"Testing corridor with receive amount: {source_currency} ({source_country}) → "
               f"{receive_amount} {destination_currency} ({destination_country})")
    
    try:
        # Get a quote
        result = provider.get_quote(
            receive_amount=Decimal(receive_amount),
            source_currency=source_currency,
            destination_currency=destination_currency,
            source_country=source_country,
            destination_country=destination_country
        )
        
        # Check if the request was successful
        if result["success"]:
            logger.info(f"✅ SUCCESS: {result['send_amount']} {result['source_currency']} → "
                       f"{receive_amount} {result['destination_currency']}")
            logger.info(f"Exchange rate: {result['exchange_rate']}")
            logger.info(f"Fee: {result['fee']}")
            return True
        else:
            logger.error(f"❌ FAILED: {result['error_message']}")
            return False
            
    except Exception as e:
        logger.error(f"❌ ERROR: {str(e)}", exc_info=True)
        return False

def test_error_handling(provider):
    """Test that the provider properly handles errors and returns standardized error responses"""
    logger = logging.getLogger("test_error_handling")
    logger.info("Testing error handling")
    
    # Test an unsupported corridor
    try:
        result = provider.get_quote(
            amount=Decimal("1000"),
            source_currency="SGD",  # Unsupported source currency with DE
            destination_currency="UAH",
            source_country="DE",
            destination_country="UA"
        )
        
        if not result["success"] and result["error_message"]:
            logger.info(f"✅ Correctly handled unsupported corridor: {result['error_message']}")
            return True
        else:
            logger.error("❌ Failed to handle unsupported corridor properly")
            return False
    except Exception as e:
        logger.error(f"❌ ERROR: Exception was raised instead of returning error response: {str(e)}")
        return False

def test_cash_pickup(provider):
    """Test corridors with cash pickup delivery method"""
    logger = logging.getLogger("test_cash_pickup")
    logger.info("Testing cash pickup delivery method")
    
    # Choose a source country/currency
    source_country = "GB"
    source_currency = "GBP"
    
    # Try to find a destination country that supports cash pickup
    for dest_country in CASH_PICKUP_COUNTRIES:
        try:
            # Get the default currency for this country
            if dest_country in COUNTRY_CURRENCIES:
                currencies = COUNTRY_CURRENCIES[dest_country]
                if isinstance(currencies, list):
                    dest_currency = currencies[0]
                else:
                    dest_currency = currencies
                
                logger.info(f"Testing cash pickup: {source_currency} ({source_country}) → "
                           f"{dest_currency} ({dest_country})")
                
                result = provider.get_quote(
                    amount=Decimal("1000"),
                    source_currency=source_currency,
                    destination_currency=dest_currency,
                    source_country=source_country,
                    destination_country=dest_country,
                    delivery_method="cash_pickup"
                )
                
                if result["success"]:
                    logger.info(f"✅ SUCCESS: Cash pickup to {dest_country} works!")
                    logger.info(f"Exchange rate: {result['exchange_rate']}")
                    logger.info(f"Fee: {result['fee']}")
                    
                    # Check if cash_pickup is in the delivery methods
                    cash_pickup_available = False
                    if "available_delivery_methods" in result:
                        for method in result["available_delivery_methods"]:
                            if method["standardized_name"] == "cash_pickup":
                                cash_pickup_available = True
                                break
                    
                    if cash_pickup_available:
                        logger.info("✅ Cash pickup delivery method found in response")
                        return True
                    else:
                        logger.warning("⚠️ Cash pickup delivery method NOT found in response")
                        return False
                else:
                    logger.warning(f"⚠️ Cash pickup test failed: {result['error_message']}")
            
        except Exception as e:
            logger.error(f"Error testing cash pickup for {dest_country}: {str(e)}")
    
    # If we got here, no cash pickup test succeeded
    logger.error("❌ Could not find a working cash pickup corridor")
    return False

def test_mobile_wallet(provider):
    """Test corridors with mobile wallet delivery method"""
    logger = logging.getLogger("test_mobile_wallet")
    logger.info("Testing mobile wallet delivery method")
    
    # Choose a source country/currency
    source_country = "GB"
    source_currency = "GBP"
    
    # Try to find a destination country that supports mobile wallet
    for dest_country in MOBILE_WALLET_COUNTRIES:
        try:
            # Get the default currency for this country
            if dest_country in COUNTRY_CURRENCIES:
                currencies = COUNTRY_CURRENCIES[dest_country]
                if isinstance(currencies, list):
                    dest_currency = currencies[0]
                else:
                    dest_currency = currencies
                
                logger.info(f"Testing mobile wallet: {source_currency} ({source_country}) → "
                           f"{dest_currency} ({dest_country})")
                
                result = provider.get_quote(
                    amount=Decimal("1000"),
                    source_currency=source_currency,
                    destination_currency=dest_currency,
                    source_country=source_country,
                    destination_country=dest_country,
                    delivery_method="mobile_wallet"
                )
                
                if result["success"]:
                    logger.info(f"✅ SUCCESS: Mobile wallet to {dest_country} works!")
                    logger.info(f"Exchange rate: {result['exchange_rate']}")
                    logger.info(f"Fee: {result['fee']}")
                    
                    # Check if mobile_wallet is in the delivery methods
                    mobile_wallet_available = False
                    if "available_delivery_methods" in result:
                        for method in result["available_delivery_methods"]:
                            if method["standardized_name"] == "mobile_wallet":
                                mobile_wallet_available = True
                                break
                    
                    if mobile_wallet_available:
                        logger.info("✅ Mobile wallet delivery method found in response")
                        return True
                    else:
                        logger.warning("⚠️ Mobile wallet delivery method NOT found in response")
                        return False
                else:
                    logger.warning(f"⚠️ Mobile wallet test failed: {result['error_message']}")
            
        except Exception as e:
            logger.error(f"Error testing mobile wallet for {dest_country}: {str(e)}")
    
    # If we got here, no mobile wallet test succeeded
    logger.error("❌ Could not find a working mobile wallet corridor")
    return False

def test_popular_corridors(provider, max_tests=5):
    """Test a sample of popular corridors"""
    logger = logging.getLogger("test_popular_corridors")
    logger.info(f"Testing up to {max_tests} popular corridors")
    
    # Shuffle the corridors to get a random sample
    corridors = POPULAR_CORRIDORS.copy()
    random.shuffle(corridors)
    
    # Limit to max_tests
    test_corridors = corridors[:max_tests]
    
    success_count = 0
    for src_country, src_currency, dst_country, dst_currency in test_corridors:
        if test_corridor(
            provider, 
            "1000", 
            src_country, 
            src_currency, 
            dst_country, 
            dst_currency
        ):
            success_count += 1
    
    logger.info(f"✅ {success_count}/{len(test_corridors)} popular corridors successful")
    return success_count > 0

def test_random_corridors(provider, count=3):
    """Test random corridors from the available countries/currencies"""
    logger = logging.getLogger("test_random_corridors")
    logger.info(f"Testing {count} random corridors")
    
    # Get list of source countries
    source_countries = get_supported_source_countries()
    
    success_count = 0
    attempts = 0
    
    while success_count < count and attempts < 10:  # limit attempts to avoid infinite loop
        attempts += 1
        
        # Pick a random source country
        src_country = random.choice(source_countries)
        
        # Get the currency for this country
        if src_country in COUNTRY_CURRENCIES:
            currencies = COUNTRY_CURRENCIES[src_country]
            if isinstance(currencies, list):
                src_currency = currencies[0]  # Use first currency if multiple
            else:
                src_currency = currencies
            
            # Get destination countries for this source
            dest_countries = get_supported_destination_countries(src_country)
            if dest_countries:
                dst_country = random.choice(dest_countries)
                
                # Get currency for destination country
                if dst_country in COUNTRY_CURRENCIES:
                    currencies = COUNTRY_CURRENCIES[dst_country]
                    if isinstance(currencies, list):
                        dst_currency = currencies[0]  # Use first currency if multiple
                    else:
                        dst_currency = currencies
                    
                    # Skip this corridor if it's in POPULAR_CORRIDORS (we test those separately)
                    if (src_country, src_currency, dst_country, dst_currency) in POPULAR_CORRIDORS:
                        continue
                    
                    logger.info(f"Testing random corridor: {src_currency} ({src_country}) → "
                               f"{dst_currency} ({dst_country})")
                    
                    if test_corridor(
                        provider, 
                        "1000", 
                        src_country, 
                        src_currency, 
                        dst_country, 
                        dst_currency
                    ):
                        success_count += 1
    
    logger.info(f"✅ {success_count}/{count} random corridors successful")
    return success_count > 0

def main():
    """Main function to run the tests"""
    parser = argparse.ArgumentParser(description='Test the TransferGo provider implementation')
    parser.add_argument('--amount', type=str, default='1000', help='Amount to send')
    parser.add_argument('--source-country', type=str, default='DE', help='Source country code')
    parser.add_argument('--source-currency', type=str, default='EUR', help='Source currency')
    parser.add_argument('--destination-country', type=str, default='UA', help='Destination country code')
    parser.add_argument('--destination-currency', type=str, default='UAH', help='Destination currency')
    parser.add_argument('--payment', type=str, help='Payment method (e.g., bank_transfer)')
    parser.add_argument('--delivery', type=str, help='Delivery method (e.g., bank_deposit)')
    parser.add_argument('--test-all', action='store_true', help='Test all supported corridors')
    parser.add_argument('--test-popular', action='store_true', help='Test popular corridors')
    parser.add_argument('--test-random', action='store_true', help='Test random corridors')
    parser.add_argument('--test-receive', action='store_true', help='Test with receive amount instead of send amount')
    parser.add_argument('--test-errors', action='store_true', help='Test error handling')
    parser.add_argument('--test-cash-pickup', action='store_true', help='Test cash pickup delivery method')
    parser.add_argument('--test-mobile-wallet', action='store_true', help='Test mobile wallet delivery method')
    parser.add_argument('--comprehensive', action='store_true', help='Run all test types')
    
    args = parser.parse_args()
    
    # Set random seed for reproducibility
    random.seed(42)
    
    # Create the provider
    provider = TransferGoProvider()
    
    try:
        if args.comprehensive:
            # Run all test types
            print("\n=== Running comprehensive tests ===\n")
            
            print("\n--- Testing error handling ---\n")
            test_error_handling(provider)
            
            print("\n--- Testing popular corridors ---\n")
            test_popular_corridors(provider, max_tests=5)
            
            print("\n--- Testing random corridors ---\n")
            test_random_corridors(provider, count=3)
            
            print("\n--- Testing receive amount ---\n")
            test_with_receive_amount(
                provider, 
                "5000", 
                "GB", 
                "GBP", 
                "PH", 
                "PHP"
            )
            
            print("\n--- Testing cash pickup delivery method ---\n")
            test_cash_pickup(provider)
            
            print("\n--- Testing mobile wallet delivery method ---\n")
            test_mobile_wallet(provider)
            
        elif args.test_errors:
            # Test error handling
            print("\n=== Testing error handling ===\n")
            test_error_handling(provider)
            
        elif args.test_popular:
            # Test popular corridors
            print("\n=== Testing popular corridors ===\n")
            test_popular_corridors(provider)
            
        elif args.test_random:
            # Test random corridors
            print("\n=== Testing random corridors ===\n")
            test_random_corridors(provider)
            
        elif args.test_receive:
            # Test with receive amount
            print(f"\n=== Testing {args.source_currency} ({args.source_country}) → "
                 f"{args.amount} {args.destination_currency} ({args.destination_country}) ===\n")
            test_with_receive_amount(
                provider, 
                args.amount, 
                args.source_country, 
                args.source_currency, 
                args.destination_country, 
                args.destination_currency
            )
            
        elif args.test_cash_pickup:
            # Test cash pickup delivery method
            print("\n=== Testing cash pickup delivery method ===\n")
            test_cash_pickup(provider)
            
        elif args.test_mobile_wallet:
            # Test mobile wallet delivery method
            print("\n=== Testing mobile wallet delivery method ===\n")
            test_mobile_wallet(provider)
            
        elif args.test_all:
            # Test all supported corridors from the mapping file
            print("\n=== Testing all supported corridors ===\n")
            
            # Define test corridors based on supported corridors
            test_corridors = []
            for source_country, source_currency, dest_country, dest_currency in POPULAR_CORRIDORS:
                test_corridors.append({
                    "source_country": source_country,
                    "source_currency": source_currency,
                    "destination_country": dest_country,
                    "destination_currency": dest_currency,
                    "amount": "1000"
                })
            
            # Limit to 10 corridors to avoid excessive API calls
            if len(test_corridors) > 10:
                print(f"Limiting to 10 corridors out of {len(test_corridors)} total")
                random.shuffle(test_corridors)
                test_corridors = test_corridors[:10]
            
            success_count = 0
            for corridor in test_corridors:
                print(f"\n--- Testing {corridor['source_currency']} ({corridor['source_country']}) → "
                     f"{corridor['destination_currency']} ({corridor['destination_country']}) ---")
                if test_corridor(
                    provider, 
                    corridor["amount"], 
                    corridor["source_country"], 
                    corridor["source_currency"], 
                    corridor["destination_country"], 
                    corridor["destination_currency"]
                ):
                    success_count += 1
                    
            print(f"\n=== Test Results: {success_count}/{len(test_corridors)} corridors successful ===")
            
        else:
            # Test a single corridor
            print(f"\n=== Testing {args.source_currency} ({args.source_country}) → "
                 f"{args.destination_currency} ({args.destination_country}) for {args.amount} {args.source_currency} ===\n")
            test_corridor(
                provider, 
                args.amount, 
                args.source_country, 
                args.source_currency, 
                args.destination_country, 
                args.destination_currency,
                args.payment,
                args.delivery
            )
    
    finally:
        # Close the provider session
        provider.close()

if __name__ == "__main__":
    main() 