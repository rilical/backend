#!/usr/bin/env python3
"""
Combined test script for the Rewire provider integration.

This script includes tests for:
1. Direct API calls to test the Rewire endpoints
2. Testing the provider through the factory
3. Testing the get_quote method with various parameters
4. Comprehensive tests for different corridors and scenarios

Example usage:
    python3 apps/providers/rewire/tests.py --help
    python3 apps/providers/rewire/tests.py --api         # Test API endpoints directly
    python3 apps/providers/rewire/tests.py --factory     # Test through provider factory
    python3 apps/providers/rewire/tests.py --quote       # Test quote functionality
    python3 apps/providers/rewire/tests.py --comprehensive  # Run all corridor tests
    python3 apps/providers/rewire/tests.py --all         # Run all tests
"""

import argparse
import sys
import json
import logging
from decimal import Decimal
from datetime import datetime
import requests

from apps.providers.factory import ProviderFactory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("rewire_test")

# Define API endpoints directly for direct API testing
RATES_URL = "https://api.rewire.to/services/rates/v3/jsonp"
PRICING_URL = "https://lights.rewire.to/public/public-pricing"

###################
# API Tests
###################

def create_session():
    """Create a basic requests session with headers"""
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15"
        ),
        "Accept": "*/*",
        "Origin": "https://www.rewire.com",
        "Referer": "https://www.rewire.com/"
    })
    return session

def test_rates_api():
    """
    Test the Rewire rates API endpoint directly.
    """
    logger.info("Testing Rewire rates API...")
    session = create_session()
    
    try:
        resp = session.get(RATES_URL, timeout=15)
        resp.raise_for_status()
        
        try:
            data = resp.json()
            
            if data:
                # Save the full response to a file for inspection
                output_file = "rewire_rates_response.json"
                with open(output_file, "w") as f:
                    json.dump(data, f, indent=2)
                logger.info(f"Full rates response saved to {output_file}")
                
                # Print summary
                print("\nRates API Response Summary:")
                print("=" * 60)
                print(f"Timestamp: {data.get('timestamp')}")
                print(f"GeoLocation: {data.get('geoLocation', 'Not provided')}")
                
                # Print sample rates for a few countries
                countries = list(data.get("rates", {}).keys())
                if countries:
                    print(f"\nSupported sending countries: {', '.join(countries)}")
                    
                    # Print sample rates for first country
                    sample_country = countries[0]
                    currencies = list(data.get("rates", {}).get(sample_country, {}).keys())
                    if currencies:
                        print(f"\nSample rates for {sample_country}:")
                        print("-" * 60)
                        for currency in currencies[:5]:  # Show first 5 currencies
                            rates = data.get("rates", {}).get(sample_country, {}).get(currency, {})
                            print(f"{currency}: Buy = {rates.get('buy')}, Sell = {rates.get('sell')}")
                
                return data
                
            else:
                logger.error("No data returned from rates API")
                return None
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Connection error fetching Rewire rates: {str(e)}")
        return None

def test_pricing_api():
    """
    Test the Rewire pricing API endpoint directly.
    """
    logger.info("Testing Rewire pricing API...")
    session = create_session()
    
    try:
        resp = session.get(PRICING_URL, timeout=15)
        resp.raise_for_status()
        
        try:
            data = resp.json()
            
            if data:
                # Save the full response to a file for inspection
                output_file = "rewire_pricing_response.json"
                with open(output_file, "w") as f:
                    json.dump(data, f, indent=2)
                logger.info(f"Full pricing response saved to {output_file}")
                
                # Print summary
                print("\nPricing API Response Summary:")
                print("=" * 60)
                print(f"Supported currencies: {', '.join(data.keys())}")
                
                # Sample pricing data for the first currency
                if len(data) > 0:
                    first_currency = list(data.keys())[0]
                    target_currencies = list(data[first_currency].keys())
                    
                    if target_currencies:
                        print(f"\nSample pricing for {first_currency}:")
                        print("-" * 60)
                        
                        for target in target_currencies[:2]:  # Show first 2 target currencies
                            tiers = data[first_currency][target]
                            print(f"{first_currency} to {target}: {len(tiers)} pricing tiers")
                            
                            for i, tier in enumerate(tiers[:3], 1):  # Show first 3 tiers
                                print(f"  Tier {i}: {tier.get('from')} to {tier.get('to')} {first_currency}")
                                print(f"    Fee: {tier.get('price')} {first_currency}")
                                print(f"    Differential FX Fee: {tier.get('differentialFxFee', 0) * 100}%")
                                print(f"    Payout Method: {tier.get('payoutMethod', 'Not specified')}")
                
                return data
                
            else:
                logger.error("No data returned from pricing API")
                return None
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON pricing data: {str(e)}")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Connection error fetching Rewire pricing: {str(e)}")
        return None

def run_api_tests():
    """Run the direct API tests"""
    print("\n" + "=" * 80)
    print("RUNNING DIRECT API TESTS")
    print("=" * 80)
    
    rates_data = test_rates_api()
    pricing_data = test_pricing_api()
    
    return rates_data is not None

###################
# Factory Tests
###################

def test_factory():
    """Test the Rewire provider through the factory"""
    print("\n" + "=" * 80)
    print("RUNNING FACTORY TESTS")
    print("=" * 80)
    
    # Get the Rewire provider from the factory
    provider = ProviderFactory.get_provider('rewire')

    if provider is None:
        logger.error("Failed to get Rewire provider from factory")
        return False
    
    # Get and print supported sending countries
    countries = provider.get_supported_countries()
    print(f'Supported sending countries: {countries[:5]}... ({len(countries)} total)')

    # Test IL -> PHP corridor
    rate = provider.get_exchange_rate(
        send_amount=Decimal('1000'),
        send_country='IL',
        send_currency='ILS',
        receive_currency='PHP'
    )

    # Print the results
    print('\nExchange Rate Result:')
    print('=' * 60)
    for key, value in rate.items():
        print(f'{key}: {value}')
        
    # Test another corridor (GB -> INR)
    rate = provider.get_exchange_rate(
        send_amount=Decimal('500'),
        send_country='GB',
        send_currency='GBP',
        receive_currency='INR'
    )

    # Print the results
    print('\nExchange Rate Result (GB -> INR):')
    print('=' * 60)
    for key, value in rate.items():
        print(f'{key}: {value}')
    
    return True

###################
# Quote Tests
###################

def print_result(result):
    """Print the quote result in a formatted way"""
    print('=' * 60)
    for key, value in result.items():
        print(f'{key}: {value}')

def test_quotes():
    """Test the get_quote method of the Rewire provider"""
    print("\n" + "=" * 80)
    print("RUNNING QUOTE TESTS")
    print("=" * 80)
    
    # Get the Rewire provider from the factory
    print("Getting Rewire provider from factory...")
    provider = ProviderFactory.get_provider('rewire')

    if provider is None:
        logger.error("Failed to get Rewire provider from factory")
        return False
    
    # List all available providers
    print(f"Available providers: {ProviderFactory.list_providers()}")
    
    # Test with USD -> PH (Philippines) with explicit send_country
    # Note: 'US' is not in the rates data, so we use another country
    print("\nTesting USD -> PH quote with GB as send_country:")
    quote = provider.get_quote(
        amount=Decimal('1000'),
        source_currency='USD',
        target_country='PHP',
        send_country='GB'  # Use GB as send_country since it's in the rates data
    )
    print_result(quote)
    
    # Test with GBP -> IN (India)
    print("\nTesting GBP -> IN quote:")
    quote = provider.get_quote(
        amount=Decimal('500'),
        source_currency='GBP',
        target_country='IN'
    )
    print_result(quote)
    
    # Test with EUR -> PHP with explicit send_country
    print("\nTesting EUR -> PHP quote with explicit send_country:")
    quote = provider.get_quote(
        amount=Decimal('750'),
        source_currency='EUR',
        target_country='PHP',
        send_country='DE'  # Specify Germany as the sending country
    )
    print_result(quote)
    
    # Test currency code for target country
    print("\nTesting GBP -> PHP (using currency code):")
    quote = provider.get_quote(
        amount=Decimal('600'),
        source_currency='GBP',
        target_country='PHP'  # Using currency code instead of country code
    )
    print_result(quote)
    
    return True

###################
# Comprehensive Tests
###################

def format_quote(quote, test_name):
    """Format a quote result for display"""
    print(f"\nTest: {test_name}")
    print("=" * 70)
    if not quote:
        print("No quote returned")
        return
    
    for key, value in quote.items():
        print(f"{key}: {value}")

def test_comprehensive():
    """Run comprehensive tests for the Rewire provider"""
    print("\n" + "=" * 80)
    print("RUNNING COMPREHENSIVE TESTS")
    print("=" * 80)
    
    factory = ProviderFactory()
    
    logger.info("Getting Rewire provider from factory...")
    provider = factory.get_provider('rewire')
    
    if provider is None:
        logger.error("Failed to get Rewire provider from factory")
        return False
    
    logger.info("Available providers: %s", factory.list_providers())
    
    # Get supported sending countries
    sending_countries = provider.get_supported_countries()
    logger.info("Supported sending countries: %s", sending_countries)
    
    # Test scenarios
    test_scenarios = [
        {
            "name": "IL to PHP (standard corridor)",
            "amount": Decimal('1000'),
            "source_currency": "ILS",
            "target_country": "PHP",
        },
        {
            "name": "GB to INR (standard corridor)",
            "amount": Decimal('500'),
            "source_currency": "GBP",
            "target_country": "INR",
        },
        {
            "name": "DE to PHP (EUR currency with specified country)",
            "amount": Decimal('750'),
            "source_currency": "EUR",
            "target_country": "PHP",
            "send_country": "DE",
        },
        {
            "name": "USD with GB as send_country (non-default country)",
            "amount": Decimal('1000'),
            "source_currency": "USD",
            "target_country": "PHP",
            "send_country": "GB",
        },
        {
            "name": "Small amount test (below minimum)",
            "amount": Decimal('5'),
            "source_currency": "GBP",
            "target_country": "INR",
        },
        {
            "name": "Large amount test",
            "amount": Decimal('10000'),
            "source_currency": "EUR",
            "target_country": "PHP",
            "send_country": "DE",
        },
        {
            "name": "Non-standard destination currency (if supported)",
            "amount": Decimal('1000'),
            "source_currency": "GBP",
            "target_country": "NGN",
        },
        {
            "name": "Likely invalid corridor test",
            "amount": Decimal('1000'),
            "source_currency": "GBP",
            "target_country": "JPY",  # Likely not supported
        }
    ]
    
    # Run all test scenarios
    for scenario in test_scenarios:
        test_name = scenario.pop("name")
        try:
            quote = provider.get_quote(**scenario)
            format_quote(quote, test_name)
        except Exception as e:
            logger.error(f"Error in test '{test_name}': {str(e)}")
            print(f"\nTest: {test_name}")
            print("=" * 70)
            print(f"ERROR: {str(e)}")
    
    return True

###################
# Main Function
###################

def main():
    """Main function to run the tests"""
    parser = argparse.ArgumentParser(description="Test Rewire provider integration")
    parser.add_argument("--api", action="store_true", help="Run direct API tests")
    parser.add_argument("--factory", action="store_true", help="Run tests through provider factory")
    parser.add_argument("--quote", action="store_true", help="Run tests for the get_quote method")
    parser.add_argument("--comprehensive", action="store_true", help="Run comprehensive tests for various corridors")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    
    args = parser.parse_args()
    
    print(f"Rewire Integration Test - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # Default to running all tests if no specific tests are requested
    run_all = args.all or not (args.api or args.factory or args.quote or args.comprehensive)
    
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
    
    # Run comprehensive tests if requested or if running all tests
    if args.comprehensive or run_all:
        comprehensive_success = test_comprehensive()
        success = success and comprehensive_success
    
    print("\nTests complete.")
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 