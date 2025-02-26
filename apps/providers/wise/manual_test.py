"""Manual test for Wise provider."""

import os
from decimal import Decimal
from pprint import pprint

from apps.providers.wise import WiseProvider

# You would normally set this as an environment variable
# or pass it directly to the provider
os.environ["WISE_API_KEY"] = "YOUR_API_KEY"  # Replace with your actual API key if testing for real

# Initialize the provider
provider = WiseProvider()

# Get exchange rate
print("Getting exchange rate from GBP to USD...")
try:
    rate_info = provider.get_exchange_rate(
        send_amount=Decimal("100"),
        send_currency="GBP",
        receive_country="US",
        receive_currency="USD"
    )
    
    print("\nExchange rate info:")
    pprint(rate_info)
    
    if rate_info:
        print(f"\nExchange rate: {rate_info['exchange_rate']}")
        print(f"Transfer fee: {rate_info['transfer_fee']} {rate_info['send_currency']}")
        print(f"Delivery time: {rate_info['delivery_time']}")
        print(f"Service: {rate_info['service_name']}")
        print(f"Send: {rate_info['send_amount']} {rate_info['send_currency']}")
        print(f"Receive: {rate_info['receive_amount']} {rate_info['receive_currency']}")
    else:
        print("No rate information available")
        
except Exception as e:
    print(f"Error: {e}")
    raise 