"""
Super Simple WireBarley API Test

This is a minimal test just to check if the API is responding.
"""

import json
import uuid
from datetime import datetime

import requests


def test_direct_api_call():
    """Make a direct API call to WireBarley."""
    # Create a session
    session = requests.Session()

    # Set basic headers
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
        }
    )

    # First visit homepage
    print("Visiting homepage...")
    homepage_url = "https://www.wirebarley.com/"
    homepage_response = session.get(homepage_url, timeout=10)
    print(f"Homepage status: {homepage_response.status_code}")

    # Print cookies
    print(f"Cookies: {session.cookies.get_dict()}")

    # Now try API call
    print("\nMaking API call...")
    source_country = "US"
    source_currency = "USD"

    # Add API-specific headers
    session.headers.update(
        {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": homepage_url,
            "Request-ID": str(uuid.uuid4()),
            "Request-Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "Device-Type": "WEB",
            "Device-Model": "Safari",
            "Lang": "en",
        }
    )

    api_url = (
        f"https://www.wirebarley.com/my/remittance/api/v1/exrate/{source_country}/{source_currency}"
    )
    print(f"URL: {api_url}")

    api_response = session.get(api_url, timeout=10)
    print(f"API status: {api_response.status_code}")

    # Try to parse JSON
    try:
        data = api_response.json()
        print("Successfully parsed JSON response")
        print(f"Response has keys: {list(data.keys())}")

        # Save response to a file
        with open("wirebarley_simple_response.json", "w") as f:
            json.dump(data, f, indent=2)
            print("\nSaved response to wirebarley_simple_response.json")

        # Check if data is null
        if data.get("data") is None:
            print("Warning: 'data' key contains a None value")
            print(f"Full response: {json.dumps(data, indent=2)}")
        else:
            # Check for exRates
            if "exRates" in data["data"]:
                ex_rates = data["data"]["exRates"]
                print(f"Found {len(ex_rates)} exchange rates")

                # Print a few
                for i, rate in enumerate(ex_rates[:3]):
                    print(
                        f"  {i+1}. {rate.get('country')}-{rate.get('currency')}: {rate.get('wbRate')}"
                    )
            else:
                print("No exchange rates found in response")

    except ValueError:
        print("Failed to parse JSON response")
        print(f"Raw response: {api_response.text[:500]}...")  # Print first 500 chars

    return api_response.status_code == 200


if __name__ == "__main__":
    print("Starting simple API test...")
    result = test_direct_api_call()
    print(f"\nTest {'PASSED' if result else 'FAILED'}")
