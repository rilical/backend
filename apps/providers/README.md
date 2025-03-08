# RemitScout Provider Framework

This directory contains the remittance provider integrations for the RemitScout platform. Each provider implements a standardized interface to ensure consistent behavior across the aggregator.

## Architecture

The provider framework is structured as follows:

```
providers/
├── base/                  # Base classes and interfaces
│   ├── provider.py        # RemittanceProvider abstract base class
│   ├── exceptions.py      # Base exception classes
│   └── __init__.py
├── utils/                 # Shared utility modules
│   ├── country_currency_standards.py  # ISO standard mappings
│   ├── currency_mapping.py            # Common currency lookups
│   └── __init__.py
├── placid/                # Placid provider implementation
│   ├── integration.py     # Provider integration class
│   ├── mapping.py         # Provider-specific mappings
│   ├── exceptions.py      # Provider-specific exceptions
│   └── __init__.py
└── [other_providers]/     # Other provider implementations
```

## Standardized Format

All provider implementations must follow the standardized response format defined in `base/provider.py`. This ensures consistent data structure across all providers and simplifies integration with the aggregator.

### Standard Response Format

```python
{
    "provider_id": "provider_name",           # Unique identifier for the provider
    "success": True/False,                    # Whether the operation succeeded
    "error_message": "Error details or None", # Details about the error (if any)
    "send_amount": 1000.0,                    # Amount to send in source currency
    "source_currency": "USD",                 # ISO-4217 source currency code
    "destination_amount": 850000.0,           # Amount received in destination currency
    "destination_currency": "IDR",            # ISO-4217 destination currency code
    "exchange_rate": 85.0,                    # Exchange rate applied
    "fee": 5.0,                               # Fee amount in source currency
    "payment_method": "bank",                 # Method used to send funds
    "delivery_method": "bank",                # Method used to deliver funds
    "delivery_time_minutes": 1440,            # Estimated delivery time in minutes
    "timestamp": "2023-03-06T22:10:00.000Z"   # ISO-8601 timestamp of the quote
}
```

### Country and Currency Standards

- Countries must use ISO-3166-1 alpha-2 codes (e.g., "US", "GB", "IN")
- Currencies must use ISO-4217 codes (e.g., "USD", "GBP", "INR")
- Providers must handle mapping between their internal codes and these standards

## Implementing a New Provider

To implement a new remittance provider, you should:

1. Create a new directory under `providers/` for the provider
2. Create provider-specific exception classes extending the base `ProviderError`
3. Implement the `RemittanceProvider` abstract base class
4. Create mapping files for any provider-specific codes to ISO standards
5. Follow the standardized response format

### Required Methods

At minimum, a provider must implement:

- `get_quote()` - Get pricing information for a money transfer
- `standardize_response()` - Convert provider-specific response to standardized format
- `get_supported_countries()` - Return list of supported countries
- `get_supported_currencies()` - Return list of supported currencies

## Example Usage

```python
from apps.providers.placid.integration import PlacidProvider

# Initialize provider
provider = PlacidProvider()

# Get a quote
quote = provider.get_quote(
    amount=Decimal('1000.00'),
    source_currency='USD',
    dest_currency='INR',
    source_country='US',
    dest_country='IN',
    payment_method='bank',
    delivery_method='bank'
)

# Check if quote was successful
if quote['success']:
    print(f"Exchange rate: {quote['exchange_rate']}")
    print(f"Amount to be received: {quote['destination_amount']} {quote['destination_currency']}")
else:
    print(f"Error: {quote['error_message']}")
```

## Error Handling

All provider-specific errors should extend the base `ProviderError` class defined in `base/exceptions.py`. This allows for consistent error handling across providers.

Example error hierarchy:
- `ProviderError` - Base class for all provider errors
  - `PlacidError` - Base class for Placid errors
    - `PlacidConnectionError` - Network or connection errors
    - `PlacidApiError` - API-specific errors
    - `PlacidResponseError` - Response parsing errors
    - `PlacidCorridorUnsupportedError` - Unsupported corridor errors 