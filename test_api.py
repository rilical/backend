#!/usr/bin/env python3
import requests
import json
import sys

def test_quotes_api():
    """Test the quotes API endpoint."""
    url = "http://localhost:8000/api/quotes/"
    params = {
        "source_country": "US",
        "dest_country": "MX",
        "source_currency": "USD",
        "dest_currency": "MXN",
        "amount": 1000
    }
    
    print(f"Testing quotes API with parameters: {params}")
    print(f"URL: {url}")
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("\nSuccess! Got response:")
            print(json.dumps(data, indent=2))
            return True
        else:
            print(f"\nError response: {response.text}")
            return False
    
    except Exception as e:
        print(f"\nException: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_quotes_api()
    sys.exit(0 if success else 1) 