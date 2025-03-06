#!/usr/bin/env python3
"""
Remitbee Comprehensive API Test Script

This script performs more extensive testing of the Remitbee integration by:
1. Testing all available corridors
2. Testing different send amounts (small, medium, large)
3. Providing detailed output and comparison between responses

Usage:
  python3 test_remitbee_comprehensive.py [path_to_html_file]

If a path to an HTML file is provided, it will parse that file for country data.
Otherwise, it will attempt to use cached country data if available.
"""

import json
import sys
import os
import logging
import time
from decimal import Decimal
from tabulate import tabulate

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Add the project root to the path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

try:
    from apps.providers.remitbee.integration import RemitbeeProvider
except ImportError:
    print("Cannot import RemitbeeProvider. Make sure you're running this script from the project root directory.")
    sys.exit(1)

# Test amounts to try for each corridor
TEST_AMOUNTS = [
    ("small", "100.00"),
    ("medium", "500.00"),
    ("large", "2000.00"),
]

def run_comprehensive_tests(html_file=None):
    """
    Run comprehensive tests for all available Remitbee corridors with different amounts.
    
    Args:
        html_file: Optional path to an HTML file containing Remitbee country data.
    """
    print("\n=== REMITBEE COMPREHENSIVE API TEST ===\n")
    
    # Initialize the provider
    if html_file:
        print(f"Initializing RemitbeeProvider with HTML file: {html_file}")
        provider = RemitbeeProvider(countries_html_file=html_file)
    else:
        print("Initializing RemitbeeProvider with cached country data")
        provider = RemitbeeProvider()
    
    # Get all supported countries
    countries = provider.get_supported_countries()
    print(f"Loaded {len(countries)} countries from Remitbee data\n")
    
    if not countries:
        print("No country data available. Please provide an HTML file with country data.")
        return
    
    # Summary tables for results
    supported_corridors = []
    unsupported_corridors = []
    error_corridors = []
    
    # Test each country
    for i, country_data in enumerate(countries):
        country_code = country_data.get("iso2")
        country_name = country_data.get("country_name")
        currency_code = country_data.get("currency_code")
        
        print(f"\n{'='*80}")
        print(f"Testing corridor {i+1}/{len(countries)}: CAD → {country_code} ({currency_code}) - {country_name}")
        
        # Test with different amounts
        for amount_label, amount in TEST_AMOUNTS:
            print(f"\n  Amount: {amount} CAD ({amount_label})")
            
            try:
                # Get exchange rate using our integration
                result = provider.get_exchange_rate(
                    send_amount=Decimal(amount),
                    send_currency="CAD",
                    receive_country=country_code
                )
                
                if result:
                    # Check if it's supported
                    if not result.get("supported", False) or "error" in result:
                        print(f"  ❌ UNSUPPORTED - {result.get('error', 'No specific error message')}")
                        if amount_label == "medium":  # Only add to summary once
                            unsupported_corridors.append({
                                "Country": f"{country_code} ({country_name})",
                                "Currency": currency_code,
                                "Error": result.get("error", "Unsupported")
                            })
                    else:
                        print(f"  ✅ SUCCESS - Got exchange rate data")
                        print(f"    Exchange Rate: {result.get('exchange_rate')}")
                        print(f"    Fee: {result.get('fee')} CAD")
                        print(f"    Receive Amount: {result.get('receive_amount')} {result.get('receive_currency')}")
                        print(f"    Delivery Time: {result.get('delivery_time')} hours")
                        
                        if amount_label == "medium":  # Only add to summary once
                            supported_corridors.append({
                                "Country": f"{country_code} ({country_name})",
                                "Currency": currency_code,
                                "Rate": result.get('exchange_rate'),
                                "Fee": result.get('fee')
                            })
                else:
                    print(f"  ❌ FAILED - No result returned")
                    if amount_label == "medium":  # Only add to summary once
                        error_corridors.append({
                            "Country": f"{country_code} ({country_name})",
                            "Currency": currency_code,
                            "Error": "No result returned"
                        })
                
                # Add a short delay to avoid rate limiting
                time.sleep(1)
                
            except Exception as e:
                print(f"  ❌ ERROR - {str(e)}")
                if amount_label == "medium":  # Only add to summary once
                    error_corridors.append({
                        "Country": f"{country_code} ({country_name})",
                        "Currency": currency_code,
                        "Error": str(e)
                    })
    
    # Print summary
    print("\n" + "="*80)
    print("SUMMARY OF RESULTS\n")
    
    print(f"Total countries tested: {len(countries)}")
    print(f"Supported corridors: {len(supported_corridors)}")
    print(f"Unsupported corridors: {len(unsupported_corridors)}")
    print(f"Error corridors: {len(error_corridors)}")
    
    # Print supported corridors
    if supported_corridors:
        print("\nSUPPORTED CORRIDORS:")
        print(tabulate(supported_corridors, headers="keys", tablefmt="grid"))
    
    # Print unsupported corridors
    if unsupported_corridors:
        print("\nUNSUPPORTED CORRIDORS:")
        print(tabulate(unsupported_corridors, headers="keys", tablefmt="grid"))
    
    # Print error corridors
    if error_corridors:
        print("\nERROR CORRIDORS:")
        print(tabulate(error_corridors, headers="keys", tablefmt="grid"))

def main():
    """
    Main entry point for the script.
    """
    # Check if an HTML file was provided
    html_file = None
    if len(sys.argv) > 1:
        html_file = sys.argv[1]
        if not os.path.exists(html_file):
            print(f"Error: HTML file '{html_file}' not found.")
            sys.exit(1)
    
    run_comprehensive_tests(html_file)

if __name__ == "__main__":
    main() 