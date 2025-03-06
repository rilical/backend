# WorldRemit Provider Integration

This module provides integration with the WorldRemit money transfer service, allowing applications to retrieve exchange rates, fees, and other information programmatically.

## Features

- Exchange rate calculation with fees
- Support for multiple payment methods (Debit Card, Credit Card)
- Support for multiple delivery methods (Bank Deposit, Mobile Money, Cash Pickup)
- Country and currency support information

## Usage

### Basic Exchange Rate Lookup

```python
from apps.providers.worldremit import WorldRemitProvider
from decimal import Decimal

# Initialize the provider
provider = WorldRemitProvider()

# Get exchange rate for sending 100 USD to Turkey (TRY)
rate_info = provider.get_exchange_rate(
    send_amount=Decimal("100.00"),
    send_currency="USD",
    receive_country="TR",
    receive_currency="TRY",
    payment_method="CreditCard"
)

print(f"Exchange rate: {rate_info['exchange_rate']} TRY/USD")
print(f"Transfer fee: {rate_info['transfer_fee']} USD")
print(f"Amount to be received: {rate_info['receive_amount']} TRY")
```

### Check Available Payment Methods

```python
# Get payment methods for sending from US to Turkey
payment_methods = provider.get_payment_methods(
    source_country="US",
    target_country="TR"
)

for method in payment_methods:
    print(f"Payment method: {method['name']}, Fee: {method['fee']}")
```

### Get Supported Countries

```python
# Get list of supported countries and their currencies
countries = provider.get_supported_countries()

for country in countries:
    print(f"{country['country_name']} ({country['country_code']}): {country['currency_code']}")
```

## Error Handling

The integration provides specific exception types that should be caught when using the API:

```python
from apps.providers.worldremit import (
    WorldRemitError,
    WorldRemitAuthenticationError,
    WorldRemitConnectionError,
    WorldRemitValidationError,
    WorldRemitRateLimitError
)

try:
    rate_info = provider.get_exchange_rate(...)
except WorldRemitAuthenticationError:
    print("Authentication failed")
except WorldRemitConnectionError:
    print("Connection to WorldRemit failed")
except WorldRemitValidationError as e:
    print(f"Validation error: {str(e)}")
except WorldRemitRateLimitError:
    print("Rate limit exceeded")
except WorldRemitError as e:
    print(f"General WorldRemit error: {str(e)}")
```

## API Notes

- WorldRemit uses a GraphQL-based API
- Exchange rates can vary based on payment method and delivery method
- Fees can differ based on corridor (source country to destination country)
- Delivery times vary by method and destination
- Some corridors may have restrictions or additional requirements

## Running Tests

To run the tests for this provider:

```bash
# Run all tests
python -m unittest apps.providers.worldremit.tests

# Run a specific test
python -m unittest apps.providers.worldremit.tests.TestWorldRemitProviderRealAPI.test_get_exchange_rate_real
``` 