# TransferGo Provider Integration

This module provides integration with the TransferGo money transfer service. It implements the RemittanceProvider interface and provides methods to fetch exchange rates and fees for international money transfers.

## Features

- Fetch real-time exchange rate quotes from TransferGo
- Support for multiple corridors (source/destination country pairs)
- Extensive multi-currency support (EUR, GBP, USD and 60+ global currencies)
- Support for 90+ receiving countries across all continents
- Multi-currency receiving options for select countries (e.g., USD/EUR to Ukraine, India, Philippines)
- Support for various delivery methods
- Access to multiple payment/delivery options with different fees and speeds
- Booking token capture for potential transaction completion
- Fallback mechanisms if API calls fail
- Standardized response format matching other provider integrations

## Requirements

- Python 3.8+
- `requests` library
- `urllib3` library 

## Usage

### Basic Usage

```python
from decimal import Decimal
from apps.providers.factory import ProviderFactory

# Get an instance of the TransferGo provider
transfergo = ProviderFactory.get_provider('transfergo')

# Get exchange rate for EUR to UAH transfer
result = transfergo.get_exchange_rate(
    send_amount=Decimal("500.00"),
    send_currency="EUR",
    receive_country="UA",
    receive_currency="UAH"
)

print(f"Exchange rate: {result['exchange_rate']}")
print(f"Fee: {result['fee']} {result['source_currency']}")
print(f"Recipient will receive: {result['destination_amount']} {result['destination_currency']}")
```

### Working with Multiple Corridors

```python
from decimal import Decimal
from apps.providers.factory import ProviderFactory

# Get an instance of the TransferGo provider
transfergo = ProviderFactory.get_provider('transfergo')

# Define several corridors to test
corridors = [
    {"currency": "EUR", "country": "PL", "dest_currency": "PLN"},
    {"currency": "EUR", "country": "RO", "dest_currency": "RON"},
    {"currency": "GBP", "country": "IN", "dest_currency": "INR"},
    {"currency": "USD", "country": "MX", "dest_currency": "MXN"}
]

# Check rates for each corridor
for corridor in corridors:
    result = transfergo.get_exchange_rate(
        send_amount=Decimal("500.00"),
        send_currency=corridor["currency"],
        receive_country=corridor["country"],
        receive_currency=corridor["dest_currency"]
    )
    
    print(f"\n{corridor['currency']} to {corridor['dest_currency']}:")
    print(f"Rate: {result['exchange_rate']}")
    print(f"Fee: {result['fee']} {result['source_currency']}")
    print(f"Destination amount: {result['destination_amount']} {result['destination_currency']}")
```

### Using Multi-Currency Receiving Options

Several countries can receive funds in both their local currency and USD/EUR. You can specify the preferred receiving currency:

```python
from decimal import Decimal
from apps.providers.factory import ProviderFactory

# Get an instance of the TransferGo provider
transfergo = ProviderFactory.get_provider('transfergo')

# Send money to Ukraine in USD instead of the default UAH
result = transfergo.get_exchange_rate(
    send_amount=Decimal("500.00"),
    send_currency="EUR",
    receive_country="UA",
    preferred_receive_currency="USD"  # Override default currency
)

print(f"Exchange rate: {result['exchange_rate']}")
print(f"Fee: {result['fee']} {result['source_currency']}")
print(f"Recipient will receive: {result['destination_amount']} {result['destination_currency']}")
```

### Getting Supported Countries and Currencies

You can get all the supported countries and currencies:

```python
from apps.providers.factory import ProviderFactory

# Get an instance of the TransferGo provider
transfergo = ProviderFactory.get_provider('transfergo')

# Get all supported countries and their available currencies
supported = transfergo.get_supported_countries_and_currencies()

# Get available sending countries
send_countries = transfergo.get_supported_send_countries()

# Print multi-currency countries
multi_currency_countries = {country: currencies 
                           for country, currencies in supported.items() 
                           if len(currencies) > 1}

print(f"Total supported countries: {len(supported)}")
print(f"Countries with multiple currency options: {len(multi_currency_countries)}")
for country, currencies in multi_currency_countries.items():
    print(f"{country}: {', '.join(currencies)}")
```

### Accessing All Payment Options

```python
from decimal import Decimal
from apps.providers.transferGo.integration import TransferGoProvider

# Use the provider directly for advanced features
transfergo = TransferGoProvider()

# Get detailed quote with all options
quote = transfergo.get_quote(
    from_country="DE",
    to_country="UA",
    from_currency="EUR",
    to_currency="UAH",
    amount=Decimal("300.00"),
    calc_base="sendAmount"
)

# Access all available options
all_options = quote.get("options", [])
print(f"Found {len(all_options)} different payment/delivery options")

# Display each option
for idx, option in enumerate(all_options, 1):
    pay_in = option.get("payInMethod", {}).get("type", "Unknown")
    pay_out = option.get("payOutMethod", {}).get("type", "Unknown")
    fee = option.get("fee", {}).get("value", "0.00")
    rate = option.get("rate", {}).get("value", "0.00")
    receive = option.get("receivingAmount", {}).get("value", "0.00")
    
    print(f"Option {idx}: {pay_in} → {pay_out}")
    print(f"  Fee: {fee} EUR, Rate: {rate}, Receive: {receive} UAH")
```

### Using with Context Manager

```python
from decimal import Decimal
from apps.providers.factory import ProviderFactory

with ProviderFactory.get_provider('transfergo') as transfergo:
    # Get exchange rates for multiple corridors
    result_eur = transfergo.get_exchange_rate(
        send_amount=Decimal("300.00"),
        send_currency="EUR",
        receive_country="PL",
        receive_currency="PLN"
    )
    
    result_gbp = transfergo.get_exchange_rate(
        send_amount=Decimal("400.00"),
        send_currency="GBP",
        receive_country="IN",
        receive_currency="INR"
    )
    
    print(f"EUR to PLN Rate: {result_eur['exchange_rate']}")
    print(f"GBP to INR Rate: {result_gbp['exchange_rate']}")
```

## Error Handling

The provider throws custom exceptions for different failure scenarios:

- `TransferGoError` - Base exception for all TransferGo-related errors
- `TransferGoAuthenticationError` - Authentication issues
- `TransferGoConnectionError` - Network connection issues
- `TransferGoValidationError` - Input validation errors
- `TransferGoRateLimitError` - Rate limit exceeded

Example of handling errors:

```python
from apps.providers.transferGo.exceptions import (
    TransferGoError, 
    TransferGoConnectionError,
    TransferGoValidationError
)

try:
    result = transfergo.get_exchange_rate(
        send_amount=Decimal("500.00"),
        send_currency="EUR",
        receive_country="UA",
        receive_currency="UAH"
    )
except TransferGoConnectionError as e:
    print(f"Connection error: {e}")
except TransferGoValidationError as e:
    print(f"Validation error: {e}")
except TransferGoError as e:
    print(f"TransferGo API error: {e}")
```

## Supported Countries and Regions

The TransferGo provider now supports a wide range of countries and currencies across all regions:

### Europe
- Eurozone countries (Germany, France, Spain, Italy, etc.)
- UK (GBP)
- Poland (PLN)
- Romania (RON)
- Czech Republic (CZK)
- Hungary (HUF)
- Sweden (SEK)
- Norway (NOK)
- Denmark (DKK)
- Switzerland (CHF)
- And more...

### Americas
- USA (USD)
- Canada (CAD)
- Mexico (MXN)
- Brazil (BRL)
- Colombia (COP)
- Argentina (ARS)
- Chile (CLP)
- Peru (PEN)
- And more...

### Asia Pacific
- Australia (AUD)
- New Zealand (NZD)
- Japan (JPY)
- China (CNY)
- Singapore (SGD)
- India (INR)
- Philippines (PHP)
- Thailand (THB)
- Vietnam (VND)
- Indonesia (IDR)
- And more...

### Middle East
- United Arab Emirates (AED)
- Saudi Arabia (SAR)
- Qatar (QAR)
- Israel (ILS)
- Turkey (TRY)
- And more...

### Africa
- South Africa (ZAR)
- Nigeria (NGN)
- Kenya (KES)
- Egypt (EGP)
- Morocco (MAD)
- Ghana (GHS)
- And more...

## Multi-Currency Receiving Countries

The following countries can receive transfers in multiple currencies:

- Ukraine (UAH, USD, EUR)
- India (INR, USD, EUR)
- Philippines (PHP, USD)
- Nigeria (NGN, USD, EUR)
- Kenya (KES, USD, EUR)
- Ghana (GHS, USD, EUR)
- Tanzania (TZS, USD, EUR)
- Uganda (UGX, USD, EUR)
- Sri Lanka (LKR, USD)
- Nepal (NPR, USD, EUR)

## Running Tests

You can run the included test script to verify the integration:

```bash
python apps/providers/transferGo/test.py
```

The test script will:
1. Test various money transfer corridors including traditional and newly added ones
2. Test multi-currency receiving options
3. Display supported countries and currencies
4. Show exchange rates, fees, and available options
5. Indicate if the provider is using live data or fallback data

## Notes

- TransferGo's API returns multiple options with different payment methods, delivery methods, speeds, and fees.
- The integration selects the default option (marked `isDefault=true` in the API response) for standardized results.
- If you need to access all available options, use the `get_quote()` method directly.
- The API provides a booking token that could be used for completing the transaction in a separate API call if needed. 
- Not all countries can be used as sending countries - refer to `get_supported_send_countries()` for the complete list. 