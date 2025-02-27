# Intermex Money Transfer Provider

This module implements the Intermex Money Transfer service integration for the RemitScout platform.

## Overview

The Intermex provider allows access to Intermex's exchange rates and money transfer services. It supports multiple corridors, delivery methods, and payment types.

## API Details

- Base URL: `https://api.imxi.com`
- API Key: Required in header as `Ocp-Apim-Subscription-Key`
- Pricing endpoint: `/pricing/api/v2/feesrates`

## Usage

Basic usage example:

```python
from apps.providers.intermex.integration import IntermexProvider

# Initialize provider
provider = IntermexProvider()

# Get exchange rate
result = provider.get_exchange_rate(
    send_amount=100.00,
    send_currency="USD",
    receive_country="TUR",
    receive_currency="TRY",
    send_country="USA"
)

print(f"Exchange rate: {result['exchange_rate']}")
print(f"Transfer fee: {result['transfer_fee']}")
print(f"Receive amount: {result['receive_amount']}")
```

## Testing

To run all the tests:
```
python3 -m unittest apps.providers.intermex.tests
```

To run a specific test:
```
python3 -m unittest apps.providers.intermex.tests.TestIntermexProviderRealAPI.test_get_exchange_rate_real
```

## Error Handling

The module uses the following exception classes:
- `IntermexError`: Base class for all Intermex errors
- `IntermexAuthenticationError`: Authentication failures
- `IntermexValidationError`: Request validation failures
- `IntermexConnectionError`: Connection issues
- `IntermexRateLimitError`: Rate limit exceeded

## Supported Features

- Calculate exchange rates and fees
- Support for multiple corridors (country pairs)
- Multiple delivery methods (bank deposit, cash pickup)
- Various payment methods (credit card, debit card)

## Request Parameters

- `DestCountryAbbr`: Destination country abbreviation (e.g., "TUR")
- `DestCurrency`: Destination currency code (e.g., "TRY")
- `OriCountryAbbr`: Origin country abbreviation (e.g., "USA")
- `OriStateAbbr`: Origin state abbreviation (e.g., "PA")
- `StyleId`: Payment style ID (typically 3)
- `TranTypeId`: Transaction type ID (typically 3)
- `DeliveryType`: Delivery type (W for withdrawal/bank deposit)
- `OriCurrency`: Origin currency code (e.g., "USD")
- `ChannelId`: Channel ID (typically 1)
- `OriAmount`: Amount to send in origin currency
- `DestAmount`: Amount to receive in destination currency (0 if calculating from OriAmount)
- `SenderPaymentMethodId`: Payment method ID (3: Debit Card, 4: Credit Card) 