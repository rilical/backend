"""
Basic WireBarley Public API Test

This test checks if we can access various public API endpoints.
It doesn't require authentication.
"""

import json
import os
import unittest
import uuid
from datetime import datetime

import requests


class TestWireBarleyPublicAPI(unittest.TestCase):
    """Test the public API for WireBarley."""

    def setUp(self):
        """Set up common headers for all tests."""
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Device-Type": "WEB",
            "Lang": "en",
            "Request-ID": str(uuid.uuid4()),
            "Request-Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
        }

        # Create a directory for response files if it doesn't exist
        os.makedirs("api_responses", exist_ok=True)

    def test_homepage(self):
        """Test access to the WireBarley homepage."""
        url = "https://www.wirebarley.com/"

        print(f"\nTesting homepage: {url}")
        response = requests.get(url, headers=self.headers, timeout=10)

        print(f"Status code: {response.status_code}")
        self.assertEqual(response.status_code, 200)
        print("Successfully accessed the homepage")

        # Save the HTML to a file
        with open("api_responses/wirebarley_homepage.html", "w", encoding="utf-8") as f:
            f.write(response.text)
            print("Saved homepage HTML for inspection")

    def test_usd_exchange_rates(self):
        """Test USD exchange rates API endpoint."""
        url = "https://www.wirebarley.com/my/remittance/api/v1/exrate/US/USD"

        print(f"\nTesting USD API endpoint: {url}")
        response = requests.get(url, headers=self.headers, cookies={"lang": "en"}, timeout=10)

        # Check the status code
        print(f"Status code: {response.status_code}")
        self.assertEqual(response.status_code, 200)

        self._process_response(response, "wirebarley_usd_response.json")

    def test_nzd_exchange_rates(self):
        """Test NZD exchange rates API endpoint."""
        url = "https://www.wirebarley.com/my/remittance/api/v1/exrate/NZ/NZD"

        print(f"\nTesting NZD API endpoint: {url}")
        response = requests.get(url, headers=self.headers, cookies={"lang": "en"}, timeout=10)

        # Check the status code
        print(f"Status code: {response.status_code}")
        self.assertEqual(response.status_code, 200)

        self._process_response(response, "wirebarley_nzd_response.json")

    def _process_response(self, response, filename):
        """Process an API response, save it, and analyze the content."""
        try:
            data = response.json()
            print("Successfully parsed JSON response")
            print(f"Response has keys: {list(data.keys())}")

            # Save response to a file for manual inspection
            with open(f"api_responses/{filename}", "w") as f:
                json.dump(data, f, indent=2)
                print(f"\nSaved complete response to api_responses/{filename}")

            # Check if the response has the expected structure
            self.assertIn("data", data)

            # Handle possible None value for data
            if data["data"] is None:
                print("Warning: 'data' key contains a None value")
                print("Full response:")
                print(json.dumps(data, indent=2))
                return

            # Check for data sub-keys
            data_section = data["data"]
            print(f"Data section type: {type(data_section).__name__}")

            if isinstance(data_section, dict):
                data_keys = list(data_section.keys())
                print(f"Data section has keys: {data_keys}")

                # Print information about exRates if available
                if "exRates" in data_section:
                    ex_rates = data_section["exRates"]
                    print(f"Found {len(ex_rates)} exchange rates")

                    # Print the first few currencies and rates
                    for i, rate in enumerate(ex_rates[:5]):
                        country = rate.get("country", "Unknown")
                        currency = rate.get("currency", "Unknown")
                        wb_rate = rate.get("wbRate", 0)
                        print(f"  {i+1}. {country}-{currency}: {wb_rate}")
                else:
                    print("No 'exRates' found in data")
            else:
                print(f"Data section is not a dictionary: {data_section}")

        except ValueError:
            print("Response is not valid JSON")
            self.fail("Response is not valid JSON")


if __name__ == "__main__":
    print("Starting WireBarley Public API Tests...")
    unittest.main()
