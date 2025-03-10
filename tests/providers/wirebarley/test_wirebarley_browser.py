"""
Browser-like WireBarley Test

This test simulates a browser session to get exchange rates from WireBarley.
"""

import unittest
import requests
import uuid
import json
import os
import time
from datetime import datetime

class TestWireBarleyBrowser(unittest.TestCase):
    """Test WireBarley using browser-like requests."""
    
    def setUp(self):
        """Set up the test session with browser-like behavior."""
        # Create a session that persists cookies
        self.session = requests.Session()
        
        # Set browser-like headers
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1"
        })
        
        # Create a directory for response files if it doesn't exist
        os.makedirs("api_responses", exist_ok=True)
    
    def test_browser_flow(self):
        """Test a complete browser flow to get exchange rates."""
        # Step 1: Visit the homepage first to get cookies
        print("\nStep 1: Visiting the homepage")
        homepage_url = "https://www.wirebarley.com/"
        homepage_response = self.session.get(homepage_url, timeout=10)
        
        print(f"Homepage status: {homepage_response.status_code}")
        self.assertEqual(homepage_response.status_code, 200)
        print(f"Cookies after homepage: {self.session.cookies.get_dict()}")
        
        # Save the HTML to a file
        with open("api_responses/wirebarley_homepage_browser.html", "w", encoding="utf-8") as f:
            f.write(homepage_response.text)
        
        # Step 2: Visit the calculator page which has the exchange rates
        print("\nStep 2: Visiting the calculator page")
        calculator_url = "https://www.wirebarley.com/"
        
        # Update headers for this specific request
        self.session.headers.update({
            "Referer": homepage_url
        })
        
        calculator_response = self.session.get(calculator_url, timeout=10)
        print(f"Calculator page status: {calculator_response.status_code}")
        self.assertEqual(calculator_response.status_code, 200)
        
        # Save the HTML to a file
        with open("api_responses/wirebarley_calculator.html", "w", encoding="utf-8") as f:
            f.write(calculator_response.text)
        
        # Step 3: Make the API request for exchange rates with the session cookies
        print("\nStep 3: Getting exchange rates")
        time.sleep(1)  # Small delay to be nice to the server
        
        # Try different source currencies
        for source_country, source_currency in [("NZ", "NZD"), ("US", "USD"), ("CA", "CAD")]:
            print(f"\nTrying {source_country}/{source_currency}")
            
            # Update headers to simulate XHR request
            self.session.headers.update({
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": calculator_url,
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "Request-ID": str(uuid.uuid4()),
                "Request-Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                "Device-Type": "WEB",
                "Device-Model": "Safari",
                "Device-Version": "605.1.15",
                "Lang": "en"
            })
            
            api_url = f"https://www.wirebarley.com/my/remittance/api/v1/exrate/{source_country}/{source_currency}"
            api_response = self.session.get(api_url, timeout=10)
            
            print(f"API status: {api_response.status_code}")
            self.assertEqual(api_response.status_code, 200)
            
            try:
                data = api_response.json()
                print(f"Response has keys: {list(data.keys())}")
                
                # Save response to a file for manual inspection
                with open(f"api_responses/wirebarley_{source_currency.lower()}_browser.json", "w") as f:
                    json.dump(data, f, indent=2)
                
                # Check if we got valid data
                if data["data"] is not None and isinstance(data["data"], dict) and "exRates" in data["data"]:
                    ex_rates = data["data"]["exRates"]
                    print(f"Found {len(ex_rates)} exchange rates")
                    
                    # Print a few sample rates
                    for i, rate in enumerate(ex_rates[:3]):
                        country = rate.get("country", "Unknown")
                        currency = rate.get("currency", "Unknown")
                        wb_rate = rate.get("wbRate", 0)
                        print(f"  {i+1}. {country}-{currency}: {wb_rate}")
                else:
                    print("No exchange rates found in response")
                    print(f"Full response: {json.dumps(data, indent=2)}")
            
            except ValueError:
                print("Failed to parse JSON response")
                with open(f"api_responses/wirebarley_{source_currency.lower()}_error.txt", "w", encoding="utf-8") as f:
                    f.write(api_response.text)

if __name__ == "__main__":
    print("Starting WireBarley Browser Tests...")
    unittest.main() 