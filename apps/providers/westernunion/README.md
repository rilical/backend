# Western Union Provider

This module implements the Western Union money transfer service integration for the RemitScout platform.

## Overview

The Western Union provider allows access to Western Union's exchange rates and money transfer services. It supports multiple corridors, delivery methods, and payment types.

## Usage

Basic usage example:

```python
from apps.providers.westernunion.integration import WesternUnionProvider

# Initialize provider
provider = WesternUnionProvider()

# Get exchange rate
rate_data = provider.get_exchange_rate(
    send_amount=500.00,
    send_currency="USD",
    receive_country="MX",
    send_country="US"
)

print(f"Exchange rate: {rate_data['exchange_rate']}")
print(f"Transfer fee: {rate_data['transfer_fee']}")
print(f"Receive amount: {rate_data['receive_amount']}")
```

## Testing

To run all the tests:
```
python3 -m unittest apps.providers.westernunion.tests
```

To run a specific test:
```
python3 -m unittest apps.providers.westernunion.tests.TestWesternUnionProviderRealAPI.test_discover_supported_methods
```

## Error Handling

The module uses the following exception classes:
- `WUError`: Base class for all Western Union errors
- `WUAuthenticationError`: Authentication failures
- `WUValidationError`: Request validation failures
- `WUConnectionError`: Connection issues

## Supported Features

- Calculate exchange rates and fees
- Support for multiple corridors (country pairs)
- Multiple delivery methods (bank deposit, cash pickup, etc.)
- Various payment methods (bank account, credit card, debit card) 