# Rewire Money Transfer Integration

## Overview

This module provides integration with Rewire, a cross-border money transfer service focused on remittances between various corridors, particularly from Israel and European countries to various destinations including Philippines, India, and China. The implementation allows fetching of exchange rates, fees, and supported corridors.

## API Details

The integration uses two main API endpoints:

1. **Rates API**: `https://api.rewire.to/services/rates/v3/jsonp`
   - Purpose: Fetch current exchange rates for various currency pairs
   - Method: GET
   - Authentication: None (public API)
   - Format: JSON
   - Status: **Working** - Returns exchange rates for multiple countries and currencies

2. **Pricing API**: `https://lights.rewire.to/public/public-pricing`
   - Purpose: Get fee tier information for supported corridors
   - Method: GET
   - Authentication: None (public API)
   - Format: JSON
   - Status: **Not Working** - Returns 500 Internal Server Error (as of March 2025)

## API Response Format

### Rates API

The rates API returns data in the following format:

```json
{
  "id": "...",
  "mid": false,
  "timestamp": 1740954759287,
  "rates": {
    "IL": {
      "NGN": {"buy": 0.00068, "sell": 1483.21},
      "PHP": {"buy": 0.01727, "sell": 58.34558},
      "INR": {"buy": 0.04189, "sell": 24.3421}
    },
    "GB": {
      "PHP": {"buy": 0.01727, "sell": 58.34558},
      "INR": {"buy": 0.04189, "sell": 24.3421}
    }
  },
  "geoLocation": "US"
}
```

Where:
- `buy`: How many local currency units you get for 1 unit of receiving currency
- `sell`: How many local currency units you pay for 1 unit of receiving currency

### Pricing API

The pricing API is expected to return fee tier information, but currently returns a 500 error. 

When working, the expected format would be:

```json
{
  "EUR": {
    "PHP": [
      {
        "to": 100,
        "from": 0,
        "price": 0,
        "payoutMethod": "bank",
        "differentialFxFee": 0.0
      },
      {
        "to": 500,
        "from": 100.01,
        "price": 2,
        "payoutMethod": "bank",
        "differentialFxFee": 0.004
      }
    ]
  }
}
```

Where:
- `to` and `from`: Define the amount range for this fee tier
- `price`: Fixed fee amount
- `differentialFxFee`: Percentage-based fee (e.g., 0.004 = 0.4%)
- `payoutMethod`: Delivery method (e.g., bank, cash)

## Supported Corridors

Based on our testing, Rewire supports corridors from:

- Israel (IL/ILS) to many destinations including:
  - Nigeria (NGN)
  - West African CFA franc (XOF)
  - Uganda (UGX)
  - China (CNY)
  - Ghana (GHS)
  - Kenya (KES)
  - Philippines (PHP)
  - India (INR)

- Also supports sending from:
  - United Kingdom (GB/GBP)
  - Germany (DE/EUR)
  - Italy (IT/EUR)
  - Spain (ES/EUR)
  - Netherlands (NL/EUR)
  - And many other European countries

## Fee Structure (Fallback Implementation)

Due to the Pricing API being unavailable, the implementation uses a static fee structure as a fallback:

```python
# Static fee mapping based on source currency
FEE_MAPPING = {
    'EUR': Decimal('2.5'),
    'GBP': Decimal('2.0'),
    'USD': Decimal('3.0'),
    'ILS': Decimal('5.0'),
    # Add more currencies as needed
}
```

This allows the system to continue functioning with reasonable fee estimates until the Pricing API becomes available again.

## Test Scripts

The integration includes a comprehensive test script (`tests.py`) that combines multiple test types:

1. **API Tests**: Direct testing of the Rewire API endpoints
   - Rates API testing
   - Pricing API testing (currently returns 500 error)

2. **Factory Tests**: Testing the provider through the factory
   - Verifies supported sending countries
   - Tests exchange rates for specific corridors

3. **Quote Tests**: Testing the get_quote method
   - Tests quotes for various corridors with different parameters
   - Handles the case where send_country needs to be explicitly specified

4. **Comprehensive Tests**: Run tests for a wide variety of scenarios
   - Tests different currencies and countries
   - Tests small and large amount transfers
   - Tests unsupported corridors

Run the tests with:
```
# Run all tests
python3 apps/providers/rewire/tests.py

# Run specific test types
python3 apps/providers/rewire/tests.py --api
python3 apps/providers/rewire/tests.py --factory
python3 apps/providers/rewire/tests.py --quote
python3 apps/providers/rewire/tests.py --comprehensive

# Run all tests explicitly
python3 apps/providers/rewire/tests.py --all
```

## Implementation Notes

- The `get_quote` method handles cases where the sending country is not directly inferred from the currency code
- For currencies like USD that might be used in multiple countries, you must specify the `send_country` parameter explicitly
- The implementation gracefully handles unsupported corridors by returning appropriate error messages
- The rates data is cached for 1 hour to reduce API calls

## Current Limitations

1. The static fee structure is an approximation and may not reflect actual fees
2. Some currency corridors may be unsupported or return inaccurate information
3. The USD currency requires explicit specification of a valid send_country (e.g., 'GB')
4. The Rates API may change without notice, requiring updates to the integration

## Implementation Details

The integration is implemented through the `RewireProvider` class, which extends the base `RemittanceProvider`. The class handles:

- Fetching and caching rates from the Rates API
- Currency and country code mappings
- Exchange rate calculation
- Fee calculation (currently zero due to Pricing API being unavailable)

## Key Methods

1. **get_exchange_rate**: Fetches exchange rate information for a specific corridor
   - Returns a dictionary with exchange rate, fee, and receive amount
   - Handles unsupported corridors gracefully

2. **get_quote**: A convenience method that delegates to get_exchange_rate
   - Takes source currency and target country as parameters
   - Infers the sending country if not provided

3. **get_supported_countries**: Returns a list of supported sending countries
   - Optionally filters countries that support a specific base currency

## Notes

- The Rates API is public and does not require authentication
- The Pricing API is currently returning 500 Internal Server Error (as of March 2025)
- Without the pricing API, we're unable to determine the fee structure, so fees are defaulted to zero
- Rates include buy and sell values, with sell being the relevant rate for most transfers
- The current implementation uses the "sell" rate, which represents how many units of sending currency are required to get 1 unit of receiving currency 