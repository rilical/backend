#!/usr/bin/env python3
"""
Test script for the RemitScout Quotes API.
"""
import sys
import requests
import json
from decimal import Decimal
from tabulate import tabulate

BASE_URL = "http://localhost:8000"
QUOTES_ENDPOINT = f"{BASE_URL}/api/quotes/"


def format_quotes_table(data):
    """Format quotes data as a table."""
    if not data.get("quotes"):
        return "No quotes available."
    
    table_data = []
    for quote in data.get("quotes", []):
        if quote.get("success", False):
            table_data.append([
                quote.get("provider_id", "Unknown"),
                quote.get("exchange_rate", "N/A"),
                quote.get("fee", "N/A"),
                quote.get("destination_amount", "N/A"),
                f"{quote.get('delivery_time_minutes', 0) / 60:.1f} hours"
            ])
    
    return tabulate(
        table_data,
        headers=["Provider", "Rate", "Fee", "Recipient Gets", "Delivery Time"],
        tablefmt="grid"
    )


def test_get_quotes():
    """Test fetching quotes from the API."""
    # Test parameters
    params = {
        "source_country": "US",
        "dest_country": "MX",
        "source_currency": "USD", 
        "dest_currency": "MXN",
        "amount": 1000,
        "sort_by": "best_rate"
    }
    
    print(f"Testing quotes API with parameters: {params}")
    print(f"Requesting: {QUOTES_ENDPOINT}")
    
    try:
        response = requests.get(QUOTES_ENDPOINT, params=params)
        
        if response.status_code == 200:
            data = response.json()
            
            print("\n✅ Request successful!")
            print(f"Elapsed time: {data.get('elapsed_seconds', 'N/A')} seconds")
            print(f"Total providers: {len(data.get('all_providers', []))}")
            print(f"Successful quotes: {len(data.get('quotes', []))}")
            print(f"From cache: {'Yes' if data.get('cache_hit', False) else 'No'}")
            
            print("\nQuotes:")
            print(format_quotes_table(data))
            
            # Save full response for debugging
            with open("quotes_response.json", "w") as f:
                json.dump(data, f, indent=2)
                print("\nFull response saved to quotes_response.json")
            
        else:
            print(f"\n❌ Request failed with status code: {response.status_code}")
            print(response.text)
    
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


if __name__ == "__main__":
    test_get_quotes() 