"""
Simple WireBarley Quote Test - Using Working Approach

A minimal test that fetches exchange rates from WireBarley using the proven approach.
"""

import requests
import json
import uuid
import time
from datetime import datetime

def get_wirebarley_quotes():
    """
    Get exchange rates from WireBarley using the approach that works.
    No complex testing, just the direct working approach.
    """
    # Step 1: Create a session that persists cookies
    session = requests.Session()
    
    # Set browser-like headers
    session.headers.update({
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
    
    # Step 1: Visit the homepage first to get cookies
    print("\nStep 1: Visiting the homepage")
    homepage_url = "https://www.wirebarley.com/"
    homepage_response = session.get(homepage_url, timeout=10)
    
    print(f"Homepage status: {homepage_response.status_code}")
    print(f"Cookies after homepage: {session.cookies.get_dict()}")
    
    # Step 2: Visit the calculator page - THIS IS CRITICAL
    print("\nStep 2: Visiting the calculator page again")
    
    # Update headers for this specific request
    session.headers.update({
        "Referer": homepage_url
    })
    
    calculator_response = session.get(homepage_url, timeout=10)
    print(f"Calculator page status: {calculator_response.status_code}")
    
    # Step 3: Make the API request for exchange rates with the session cookies
    print("\nStep 3: Getting exchange rates")
    time.sleep(1)  # Small delay to be nice to the server
    
    results = {}
    
    # Define source currencies to test - more options
    source_currencies = [
        ("US", "USD"),   # US Dollar
        ("NZ", "NZD"),   # New Zealand Dollar
        ("CA", "CAD"),   # Canadian Dollar
        ("AU", "AUD"),   # Australian Dollar
        ("GB", "GBP"),   # British Pound
        ("EU", "EUR")    # Euro
    ]
    
    # Test each source currency
    for source_country, source_currency in source_currencies:
        print(f"\nTrying {source_country}/{source_currency}")
        
        # Update headers to simulate XHR request
        session.headers.update({
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": homepage_url,
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
        api_response = session.get(api_url, timeout=10)
        
        print(f"API status: {api_response.status_code}")
        
        # Save the response for debugging
        with open(f"wirebarley_{source_currency.lower()}_response.json", "w") as f:
            json.dump(api_response.json(), f, indent=2)
        
        try:
            data = api_response.json()
            print(f"Response has keys: {list(data.keys())}")
            
            # Check if we got valid data
            if data.get("data") is not None and isinstance(data["data"], dict) and "exRates" in data["data"]:
                ex_rates = data["data"]["exRates"]
                print(f"Found {len(ex_rates)} exchange rates")
                
                # Print the first three rates
                for i, rate in enumerate(ex_rates[:3]):
                    country = rate.get("country", "Unknown")
                    currency = rate.get("currency", "Unknown")
                    wb_rate = rate.get("wbRate", 0)
                    print(f"  {i+1}. {country}-{currency}: {wb_rate}")
                
                # Extract and print common destination currencies for this source
                common_destinations = ["PHP", "INR", "KRW", "VND", "CNY", "JPY"]
                print("\nCommon destination rates:")
                for dest in common_destinations:
                    for rate in ex_rates:
                        if rate.get("currency") == dest:
                            print(f"  {source_currency} to {dest}: {rate.get('wbRate', 0)}")
                            break
                    
                # Store the results
                results[source_currency] = data
            else:
                print("No exchange rates found in response")
        
        except ValueError:
            print("Failed to parse JSON response")
    
    return results

def test_calculate_quotes():
    """Calculate actual quotes for specific amounts and corridors and verify standardized formats."""
    print("\n\n" + "="*50)
    print("CALCULATING SAMPLE QUOTES")
    print("="*50)
    
    # Get the exchange rate data first
    exchange_rates = get_wirebarley_quotes()
    
    # Define test cases - amount, source currency, destination currency
    test_cases = [
        (500, "USD", "PHP"),
        (1000, "USD", "INR"),
        (2000, "USD", "KRW"),
        (500, "AUD", "PHP"),
        (1000, "GBP", "INR"),
        (2000, "EUR", "VND")
    ]
    
    # Create an instance of the WireBarley provider to test standardized responses
    try:
        from apps.providers.wirebarley.integration import WireBarleyProvider
        provider = WireBarleyProvider()
        
        # First test corridors to make sure they return in the right format
        print("\nTesting provider corridors with standardized format")
        for source, _ in [("USD", ""), ("NZD", ""), ("GBP", "")]:
            print(f"\nGetting corridors for {source}")
            corridors_result = provider.get_corridors(source_currency=source)
            
            # Check structure
            print(f"Success: {corridors_result['success']}")
            if corridors_result['success']:
                print(f"Provider ID: {corridors_result['provider_id']}")
                print(f"Number of corridors: {len(corridors_result['corridors'])}")
                
                # Check first corridor
                if corridors_result['corridors']:
                    first = corridors_result['corridors'][0]
                    print(f"First corridor: {first['source_currency']} to {first['target_currency']}")
                    print(f"  Min amount: {first['min_amount']}")
                    print(f"  Max amount: {first['max_amount']}")
        
        # Test quotes with standardized format
        print("\nTesting provider quotes with standardized format")
        for amount, source, dest in test_cases:
            print(f"\nGetting quote for {amount} {source} to {dest}")
            
            # Get standardized quote
            quote_result = provider.get_quote(
                amount=amount,
                source_currency=source,
                destination_currency=dest
            )
            
            # Check response structure
            print(f"Success: {quote_result['success']}")
            
            if quote_result['success']:
                # Verify all required fields are present
                required_fields = [
                    'provider_id', 'send_amount', 'send_currency', 
                    'receive_amount', 'receive_currency', 'exchange_rate', 
                    'fee', 'payment_method', 'delivery_method', 
                    'delivery_time_minutes', 'timestamp'
                ]
                
                missing = [field for field in required_fields if field not in quote_result]
                if missing:
                    print(f"WARNING: Missing required fields: {missing}")
                else:
                    print("All required fields present ✓")
                
                # Print quote details
                print(f"  Provider: {quote_result['provider_id']}")
                print(f"  Exchange rate: {quote_result['exchange_rate']}")
                print(f"  Fee: {quote_result['fee']} {quote_result['send_currency']}")
                print(f"  Send: {quote_result['send_amount']} {quote_result['send_currency']}")
                print(f"  Receive: {quote_result['receive_amount']} {quote_result['receive_currency']}")
                print(f"  Payment method: {quote_result['payment_method']}")
                print(f"  Delivery method: {quote_result['delivery_method']}")
                print(f"  Delivery time: {quote_result['delivery_time_minutes']} minutes")
            else:
                print(f"  Error: {quote_result.get('error_message', 'Unknown error')}")
                
    except ImportError:
        print("Cannot import WireBarleyProvider - skipping standardized response tests")
        
    # Continue with manual quote calculation
    print("\nManual quote calculations")
    for amount, source, dest in test_cases:
        print(f"\nCalculating quote: {amount} {source} to {dest}")
        
        if source not in exchange_rates:
            print(f"  No data available for {source}")
            continue
            
        # Find the destination currency in the exchange rates
        data = exchange_rates[source]
        dest_rate = None
        
        for rate in data["data"]["exRates"]:
            if rate.get("currency") == dest:
                dest_rate = rate
                break
                
        if not dest_rate:
            print(f"  No rate found for {dest}")
            continue
            
        # Calculate same values provider would
        exchange_rate = dest_rate.get("wbRate", 0)
        print(f"  Base rate: {exchange_rate}")
        
        # Get threshold-based rate if applicable
        if "wbRateData" in dest_rate:
            wb_rate_data = dest_rate["wbRateData"]
            thresholds = []
            
            # Collect all thresholds
            for i in range(9):  # Up to threshold8/wbRate8
                threshold_key = f"threshold{i if i > 0 else ''}"
                rate_key = f"wbRate{i if i > 0 else ''}"
                
                if threshold_key in wb_rate_data and wb_rate_data[threshold_key] is not None:
                    threshold = float(wb_rate_data[threshold_key])
                    rate = float(wb_rate_data[rate_key])
                    thresholds.append((threshold, rate))
            
            # Sort thresholds
            thresholds.sort(key=lambda x: x[0])
            
            # Find applicable rate
            applicable_rate = exchange_rate
            for threshold, rate in thresholds:
                if amount <= threshold:
                    applicable_rate = rate
                    break
                    
            print(f"  Threshold-based rate: {applicable_rate}")
            exchange_rate = applicable_rate
        
        # Find the fee
        fee = 0
        if "transferFees" in dest_rate:
            for fee_struct in dest_rate["transferFees"]:
                min_amt = float(fee_struct.get("min", 0))
                max_amt = float(fee_struct.get("max", float('inf')))
                
                if min_amt <= amount <= max_amt:
                    # Find the applicable fee based on thresholds
                    fee = float(fee_struct.get("fee1", 0))
                    
                    # Check thresholds
                    if "threshold1" in fee_struct and fee_struct["threshold1"] is not None:
                        threshold1 = float(fee_struct["threshold1"])
                        if amount >= threshold1 and "fee2" in fee_struct and fee_struct["fee2"] is not None:
                            fee = float(fee_struct["fee2"])
                    
                    if "threshold2" in fee_struct and fee_struct["threshold2"] is not None:
                        threshold2 = float(fee_struct["threshold2"])
                        if amount >= threshold2 and "fee3" in fee_struct and fee_struct["fee3"] is not None:
                            fee = float(fee_struct["fee3"])
                    
                    break
                    
        print(f"  Fee: {fee} {source}")
        
        # Calculate destination amount
        destination_amount = amount * exchange_rate
        print(f"  Destination amount: {destination_amount:.2f} {dest}")
        print(f"  QUOTE: {amount} {source} = {destination_amount:.2f} {dest} (Rate: {exchange_rate}, Fee: {fee})")

if __name__ == "__main__":
    print("Starting WireBarley Simple Quote Test...")
    exchange_rates = get_wirebarley_quotes()
    
    # Check if we got any rates
    if not exchange_rates:
        print("\nFailed to get any exchange rates.")
    else:
        print(f"\nSuccessfully retrieved exchange rates for {len(exchange_rates)} currencies.")
        print("See the JSON files for complete data.")
        
        # Test calculating actual quotes
        test_calculate_quotes() 