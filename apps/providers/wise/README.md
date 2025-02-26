# Wise (TransferWise) Integration

This module implements the integration with Wise (formerly TransferWise) for money transfer services.

## API Overview

The Wise API provides several endpoints for money transfer operations. This integration primarily uses:

1. **Quotes Endpoint** (`/v3/quotes/`)
   - Used to get exchange rates, fees, and delivery times
   - Returns available payment options for a given currency pair

## Integration Features

The `WiseProvider` class implements the following functionality:

- Exchange rate calculation
- Fee calculation
- Delivery method selection
- Payment method selection
- Best option determination (lowest fee)

## Payment Methods (payIn)

The Wise API supports multiple payment methods:

- `PISP`: Open Banking / Instant Bank Transfer
- `BANK_TRANSFER`: Regular bank transfer
- `DEBIT`: Debit card
- `CREDIT`: Credit card
- `INTERNATIONAL_DEBIT`: International debit card
- `INTERNATIONAL_CREDIT`: International credit card
- `SWIFT`: SWIFT transfer
- `BALANCE`: Wise account balance

## Delivery Methods (payOut)

Delivery methods include:

- `BANK_TRANSFER`: Bank account deposit
- `SWIFT`: SWIFT transfer to bank account
- `CASH_PICKUP`: Cash pickup (where available)

## Error Handling

The integration implements custom exceptions:

- `WiseError`: Base class for all Wise errors
- `WiseAuthenticationError`: Authentication failures
- `WiseValidationError`: Invalid input parameters
- `WiseConnectionError`: Network or API connectivity issues

## Usage Example

```python
from decimal import Decimal
from apps.providers.wise import WiseProvider

# Initialize the provider
provider = WiseProvider(api_key="your_api_key")

# Get exchange rate
rate_info = provider.get_exchange_rate(
    send_amount=Decimal("100"),
    send_currency="USD",
    receive_country="MX"
)

# Result contains exchange rate, fees, delivery time, etc.
print(f"Exchange rate: {rate_info['exchange_rate']}")
print(f"Transfer fee: {rate_info['transfer_fee']} {rate_info['send_currency']}")
print(f"Delivery time: {rate_info['delivery_time']}")
```

## Testing

The integration includes comprehensive unit tests covering:

- Quote retrieval
- Exchange rate calculation
- Error handling
- Parameter validation
- HTTP error handling
- Currency and country mapping

Run tests with:

```
python -m unittest apps.providers.wise.tests
``` 