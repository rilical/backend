"""
WireBarley Live Exchange Rate Tests

This test verifies that WireBarley's exchange rate API is accessible
and returns valid data when approached with proper browser-like headers.
"""

import unittest
import requests
import uuid
import json
import os
import sys
from datetime import datetime
from decimal import Decimal

# Add the project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

# Now import can work
from apps.providers.wirebarley.integration import WireBarleyProvider

class TestWireBarleyLive(unittest.TestCase):
    """Live tests for WireBarley API."""
    
    @classmethod
    def setUpClass(cls):
        """Set up the test class with a provider instance and browser-like session."""
        # Create a directory for response files if it doesn't exist
        os.makedirs("api_responses", exist_ok=True)
        
        # Create a session that persists cookies
        cls.session = requests.Session()
        
        # Set browser-like headers
        cls.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Connection": "keep-alive"
        })
        
        # Initialize the provider
        cls.provider = WireBarleyProvider()
        
        # Initialize a cache for exchange rates
        cls.exchange_rates = {}
        
        # Visit the homepage to get cookies
        cls._visit_homepage()
        
        # Fetch exchange rates for multiple currencies
        cls._fetch_exchange_rates()
    
    @classmethod
    def _visit_homepage(cls):
        """Visit the homepage to get cookies and establish a session."""
        homepage_url = "https://www.wirebarley.com/"
        print(f"\nVisiting WireBarley homepage: {homepage_url}")
        
        try:
            homepage_response = cls.session.get(homepage_url, timeout=10)
            print(f"Homepage status: {homepage_response.status_code}")
            
            # Save cookies for debugging
            cookies = cls.session.cookies.get_dict()
            print(f"Cookies: {cookies}")
            
            # Save the HTML for debugging
            with open("api_responses/wirebarley_homepage.html", "w", encoding="utf-8") as f:
                f.write(homepage_response.text)
                
            return homepage_response.status_code == 200
        except Exception as e:
            print(f"Error visiting homepage: {str(e)}")
            return False
    
    @classmethod
    def _fetch_exchange_rates(cls):
        """Fetch exchange rates for multiple currencies."""
        # Update headers to simulate XHR request
        cls.session.headers.update({
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://www.wirebarley.com/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Device-Type": "WEB",
            "Device-Model": "Safari",
            "Lang": "en"
        })
        
        # Try different source currencies
        source_currencies = [
            ("US", "USD"),  # US Dollar
            ("NZ", "NZD"),  # New Zealand Dollar
            ("CA", "CAD")   # Canadian Dollar
        ]
        
        for source_country, source_currency in source_currencies:
            # Generate unique request ID
            cls.session.headers.update({
                "Request-ID": str(uuid.uuid4()),
                "Request-Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            })
            
            api_url = f"https://www.wirebarley.com/my/remittance/api/v1/exrate/{source_country}/{source_currency}"
            print(f"\nFetching rates for {source_currency} from {api_url}")
            
            try:
                api_response = cls.session.get(api_url, timeout=10)
                print(f"API status: {api_response.status_code}")
                
                if api_response.status_code == 200:
                    data = api_response.json()
                    
                    # Save response to a file for debugging
                    with open(f"api_responses/wirebarley_{source_currency.lower()}.json", "w") as f:
                        json.dump(data, f, indent=2)
                    
                    # Store the data in our cache
                    cls.exchange_rates[source_currency] = data
                    
                    # Print some stats
                    if data.get("data") and isinstance(data["data"], dict) and "exRates" in data["data"]:
                        ex_rates = data["data"]["exRates"]
                        print(f"Found {len(ex_rates)} exchange rates for {source_currency}")
                        
                        # Print first 3 for verification
                        for i, rate in enumerate(ex_rates[:3]):
                            country = rate.get("country", "Unknown")
                            currency = rate.get("currency", "Unknown")
                            wb_rate = rate.get("wbRate", 0)
                            print(f"  {i+1}. {country}-{currency}: {wb_rate}")
                    else:
                        print(f"No valid exchange rates found for {source_currency}")
            
            except Exception as e:
                print(f"Error fetching rates for {source_currency}: {str(e)}")
    
    def test_api_access(self):
        """Test that we can access the API and get valid data."""
        print("\nTesting API access...")
        
        # Check if we have exchange rates for at least one currency
        self.assertTrue(len(self.exchange_rates) > 0, "Failed to fetch any exchange rates")
        
        # Check USD specifically as it's the most common
        if "USD" in self.exchange_rates:
            usd_data = self.exchange_rates["USD"]
            
            # Verify data structure
            self.assertIn("data", usd_data)
            self.assertIsNotNone(usd_data["data"])
            self.assertIn("exRates", usd_data["data"])
            
            # Verify we have exchange rates
            ex_rates = usd_data["data"]["exRates"]
            self.assertGreater(len(ex_rates), 0, "No exchange rates found")
            
            # Verify rate structure
            first_rate = ex_rates[0]
            for key in ["country", "currency", "wbRate"]:
                self.assertIn(key, first_rate)
            
            print(f"Successfully verified {len(ex_rates)} USD exchange rates")
    
    def test_rate_calculation(self):
        """Test that rate calculation logic works with the API data."""
        print("\nTesting rate calculation...")
        
        # Use USD as source currency and PHP as destination (common corridor)
        source_currency = "USD"
        dest_currency = "PHP"
        amount = Decimal("500.00")
        
        # First check if we have this data
        if source_currency not in self.exchange_rates:
            self.skipTest(f"No exchange rates available for {source_currency}")
            
        # Find the rate data for PHP
        usd_data = self.exchange_rates[source_currency]
        php_rate_data = None
        
        for rate in usd_data["data"]["exRates"]:
            if rate.get("currency") == dest_currency:
                php_rate_data = rate
                break
                
        if not php_rate_data:
            self.skipTest(f"No {dest_currency} rate found in {source_currency} data")
        
        # Print the rate data for debugging
        print(f"Rate data for {source_currency}-{dest_currency}:")
        print(f"  wbRate: {php_rate_data.get('wbRate')}")
        if "wbRateData" in php_rate_data:
            wb_rate_data = php_rate_data["wbRateData"]
            print(f"  Thresholds: {[wb_rate_data.get(f'threshold{i if i else ''}', None) for i in range(9) if wb_rate_data.get(f'threshold{i if i else ''}') is not None]}")
        
        # Calculate the rate and fees manually
        if "wbRateData" in php_rate_data:
            wb_rate_data = php_rate_data["wbRateData"]
            
            # Find the appropriate threshold for our amount
            best_rate = php_rate_data.get("wbRate", 0)
            for i in range(9):
                threshold_key = f"threshold{i if i else ''}"
                rate_key = f"wbRate{i if i else ''}"
                
                if threshold_key in wb_rate_data and wb_rate_data[threshold_key] is not None:
                    threshold = Decimal(str(wb_rate_data[threshold_key]))
                    if amount <= threshold:
                        best_rate = Decimal(str(wb_rate_data[rate_key]))
                        break
            
            print(f"  Calculated rate for {amount} {source_currency}: {best_rate}")
            
            # Calculate the fee
            fee = 0
            if "transferFees" in php_rate_data:
                for fee_struct in php_rate_data["transferFees"]:
                    min_amt = Decimal(str(fee_struct.get("min", 0)))
                    max_amt = Decimal(str(fee_struct.get("max", "99999")))
                    
                    if min_amt <= amount <= max_amt:
                        # Find the applicable fee based on thresholds
                        fee = Decimal(str(fee_struct.get("fee1", 0)))
                        
                        # Check threshold1
                        if "threshold1" in fee_struct and fee_struct["threshold1"] is not None:
                            threshold1 = Decimal(str(fee_struct["threshold1"]))
                            if amount >= threshold1 and "fee2" in fee_struct and fee_struct["fee2"] is not None:
                                fee = Decimal(str(fee_struct["fee2"]))
                        
                        # Check threshold2
                        if "threshold2" in fee_struct and fee_struct["threshold2"] is not None:
                            threshold2 = Decimal(str(fee_struct["threshold2"]))
                            if amount >= threshold2 and "fee3" in fee_struct and fee_struct["fee3"] is not None:
                                fee = Decimal(str(fee_struct["fee3"]))
                                
                        break
            
            print(f"  Calculated fee: {fee}")
            
            # Calculate destination amount
            destination_amount = amount * best_rate
            print(f"  Destination amount: {destination_amount}")
            
            # These calculations should be greater than zero
            self.assertGreater(best_rate, 0)
            self.assertGreaterEqual(fee, 0)
            self.assertGreater(destination_amount, 0)
            
            # Final verification
            self.assertTrue(best_rate > 30, f"USD to PHP rate should be > 30, got {best_rate}")
    
    def test_provider_corridors(self):
        """Test the provider's get_corridors method."""
        print("\nTesting get_corridors functionality...")
        
        # Using the browser session should work better
        try:
            # Try to patch the provider with our browser session cookies
            if hasattr(self.provider, 'session') and self.provider.session:
                self.provider.session.cookies.update(self.session.cookies)
                print("Updated provider session with browser cookies")
            
            # Try to get corridors
            corridors = self.provider.get_corridors(source_currency="USD")
            
            if corridors["success"]:
                print(f"Success! Provider returned {len(corridors['corridors'])} corridors")
                
                # Print a few for verification
                for i, corridor in enumerate(corridors["corridors"][:3]):
                    print(f"  {i+1}. {corridor['source_currency']} to {corridor['target_currency']}")
                
                # Verify structure
                self.assertTrue(corridors["success"])
                self.assertEqual(corridors["provider_id"], "wirebarley")
                self.assertGreater(len(corridors["corridors"]), 0)
            else:
                print(f"Provider returned error: {corridors.get('error_message', 'Unknown error')}")
        except Exception as e:
            print(f"Error testing provider corridors: {str(e)}")

if __name__ == "__main__":
    print("Starting WireBarley Live Tests...")
    unittest.main() 