# RIA Money Transfer Provider

This module implements the RIA Money Transfer service integration for the RemitScout platform.

## Overview

The RIA provider allows access to RIA's exchange rates and money transfer services. It supports multiple corridors, delivery methods, and payment types.

## Usage

Basic usage example:

```python
from apps.providers.ria.integration import RIAProvider

# Initialize provider
provider = RIAProvider()

# Get exchange rate
result = provider.calculate_rate(
    send_amount=500.00,
    send_currency="USD",
    receive_country="MX",
    payment_method="DebitCard",
    delivery_method="BankDeposit",
    send_country="US"
)

print(f"Exchange rate: {result['exchange_rate']}")
print(f"Transfer fee: {result['transfer_fee']}")
print(f"Receive amount: {result['receive_amount']}")
```

## Testing

To run all the tests:
```
python3 -m unittest apps.providers.ria.tests
```

To run a specific test:
```
python3 -m unittest apps.providers.ria.tests.TestRIAProviderRealAPI.test_discover_supported_methods
```

## Error Handling

The module uses the following exception classes:
- `RIAError`: Base class for all RIA errors
- `RIAAuthenticationError`: Authentication failures
- `RIAValidationError`: Request validation failures
- `RIAConnectionError`: Connection issues

## Supported Features

- Calculate exchange rates and fees
- Support for multiple corridors (country pairs)
- Multiple delivery methods (bank deposit, cash pickup, etc.)
- Various payment methods (bank account, credit card, debit card) 