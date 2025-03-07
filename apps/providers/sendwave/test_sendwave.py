#!/usr/bin/env python3
"""
Test script for the Sendwave provider implementation.
This script tests the SendwaveProvider with live APIs and standard mappings.
"""

import sys
import logging
import argparse
from decimal import Decimal
import json

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add the parent directory to the path so we can import the provider
sys.path.insert(0, '../../..')

# Import the provider
from apps.providers.sendwave.integration import SendwaveProvider

def format_json(data):
    """Format JSON data for pretty printing"""
    return json.dumps(data, indent=2, sort_keys=True)

def test_corridor(provider, amount, source_currency, dest_country, payment_method=None, delivery_method=None):
    """Test a specific corridor with the provider"""
    logger = logging.getLogger("test_corridor")
    
    logger.info(f"Testing corridor: {source_currency} → {dest_country} for {amount} {source_currency}")
    
    try:
        # Get a quote
        result = provider.get_quote(
            amount=Decimal(amount),
            source_currency=source_currency,
            dest_country=dest_country,
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
            
            # Check if promotions are available
            if "promotions" in result and result["promotions"]:
                logger.info(f"Promotions: {len(result['promotions'])}")
                for promo in result["promotions"]:
                    logger.info(f"  - {promo['description']} (value: {promo['value']})")
            
            return True
        else:
            logger.error(f"❌ FAILED: {result['error_message']}")
            return False
            
    except Exception as e:
        logger.error(f"❌ ERROR: {str(e)}", exc_info=True)
        return False

def main():
    """Main function to run the tests"""
    parser = argparse.ArgumentParser(description='Test the Sendwave provider implementation')
    parser.add_argument('--amount', type=str, default='500', help='Amount to send')
    parser.add_argument('--currency', type=str, default='USD', help='Source currency')
    parser.add_argument('--country', type=str, default='PH', help='Destination country code')
    parser.add_argument('--payment', type=str, help='Payment method')
    parser.add_argument('--delivery', type=str, help='Delivery method')
    parser.add_argument('--test-all', action='store_true', help='Test all supported corridors')
    parser.add_argument('--test-normalize', action='store_true', help='Test normalization of country codes')
    
    args = parser.parse_args()
    
    # Create the provider
    provider = SendwaveProvider()
    
    try:
        if args.test_normalize:
            # Test country code normalization
            print("\n=== Testing country code normalization ===\n")
            
            # Define test cases with different country code formats
            normalization_tests = [
                {"source_currency": "USD", "dest_country": "phl", "amount": "500"},  # 3-letter code for Philippines
                {"source_currency": "USD", "dest_country": "Kenya", "amount": "500"},  # Country name
                {"source_currency": "EUR", "dest_country": "ph", "amount": "500"},  # Lowercase code
                {"source_currency": "GBP", "dest_country": "PHL", "amount": "500"},  # Uppercase 3-letter code
            ]
            
            success_count = 0
            for test in normalization_tests:
                print(f"\n--- Testing normalization: {test['source_currency']} → {test['dest_country']} ---")
                if test_corridor(
                    provider, 
                    test["amount"], 
                    test["source_currency"], 
                    test["dest_country"]
                ):
                    success_count += 1
                    
            print(f"\n=== Normalization Test Results: {success_count}/{len(normalization_tests)} tests successful ===")
            
        elif args.test_all:
            # Test all supported corridors
            print("\n=== Testing all supported corridors ===\n")
            
            # Define test corridors
            test_corridors = [
                # USD corridors
                {"source_currency": "USD", "dest_country": "PH", "amount": "500"},  # Philippines
                {"source_currency": "USD", "dest_country": "KE", "amount": "500"},  # Kenya
                {"source_currency": "USD", "dest_country": "GH", "amount": "500"},  # Ghana
                {"source_currency": "USD", "dest_country": "UG", "amount": "500"},  # Uganda
                
                # EUR corridors
                {"source_currency": "EUR", "dest_country": "PH", "amount": "500"},  # Philippines
                {"source_currency": "EUR", "dest_country": "KE", "amount": "500"},  # Kenya
                
                # GBP corridors
                {"source_currency": "GBP", "dest_country": "PH", "amount": "500"},  # Philippines
                {"source_currency": "GBP", "dest_country": "KE", "amount": "500"},  # Kenya
            ]
            
            success_count = 0
            for corridor in test_corridors:
                print(f"\n--- Testing {corridor['source_currency']} → {corridor['dest_country']} ---")
                if test_corridor(
                    provider, 
                    corridor["amount"], 
                    corridor["source_currency"], 
                    corridor["dest_country"]
                ):
                    success_count += 1
                    
            print(f"\n=== Test Results: {success_count}/{len(test_corridors)} corridors successful ===")
            
        else:
            # Test a single corridor
            print(f"\n=== Testing {args.currency} → {args.country} for {args.amount} {args.currency} ===\n")
            test_corridor(
                provider, 
                args.amount, 
                args.currency, 
                args.country,
                args.payment,
                args.delivery
            )
    
    finally:
        # Close the provider session
        provider.close()

if __name__ == "__main__":
    main() 