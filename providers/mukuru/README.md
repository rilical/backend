# Mukuru Money Transfer Integration

## Overview

This module provides integration with Mukuru, a cross-border money transfer service primarily focused on remittances from South Africa to various African countries including Zimbabwe, Ghana, Nigeria, Mozambique, and Malawi. The implementation allows fetching of exchange rates, fees, and supported corridors.

## API Details

The integration uses two main API endpoints:

1. **Countries API**: `https://mobile.mukuru.com/pricechecker/get_recipient_countries`
   - Purpose: Fetch list of recipient countries and their currencies
   - Method: GET
   - Parameters:
     - `brand_id`: 1
     - `sales_channel`: "mobi"
   - Authentication: None (public API)
   - Format: JSON
   - Status: **Working** - Returns list of countries and their currencies

2. **Pricechecker API**: `https://mobile.mukuru.com/pricechecker/calculate`
   - Purpose: Get exchange rate, fee, and amount information for money transfers
   - Method: GET
   - Parameters:
     - `from_currency_iso`: Currency code (e.g., "ZAR")
     - `payin_amount`: Amount to send (e.g., "900")
     - `from_country`: Sending country (e.g., "ZA")
     - `to_country`: Receiving country (e.g., "ZW")
     - `currency_id`: Internal Mukuru ID for the corridor (e.g., 18 for ZA→ZW)
     - `active_input`: "payin_amount"
     - `brand_id`: 1
     - `sales_channel`: "mobi"
   - Authentication: None (public API)
   - Format: JSON
   - Status: **Working** - Returns exchange rate, fee, and amount information

## API Response Format

### Countries API

The Countries API returns data in the following format:

```json
{
  "status": "success",
  "data": {
    "ZW": {
      "country_name": "Zimbabwe",
      "currency_market_iso": "USD",
      "...": "..."
    },
    "GH": {
      "country_name": "Ghana",
      "currency_market_iso": "GHS",
      "...": "..."
    },
    "...": "..."
  }
}
```

Where:
- `country_name`: The full name of the country
- `currency_market_iso`: The ISO currency code for the country

### Pricechecker API

The Pricechecker API returns data in the following format:

```json
{
  "status": "success",
  "data": {
    "payin_amount": 936,
    "payout_amount": 50,
    "rate_message": "Rate $1:R18.7248",
    "...": "...",
    "breakdown": {
      "Rate": "$1:R18.7248",
      "payin": {
        "Send": "ZAR936.00",
        "Charge": "ZAR94.00",
        "Total to pay": "ZAR1,030.00"
      },
      "payout": {
        "They receive": "USD50.00"
      }
    }
  }
}
```

Where:
- `payin_amount`: The amount being sent
- `payout_amount`: The amount being received
- `rate_message`: A message describing the exchange rate
- `breakdown`: A breakdown of the transaction
  - `Rate`: The exchange rate (e.g., "$1:R18.7248" means 1 USD = 18.7248 ZAR)
  - `payin`: Information about what the sender pays
    - `Send`: The amount being sent
    - `Charge`: The fee for the transaction
    - `Total to pay`: The total amount including the fee
  - `payout`: Information about what the receiver gets
    - `They receive`: The amount the receiver gets

## Supported Corridors

Based on our testing, Mukuru supports corridors from:

- South Africa (ZA/ZAR) to many destinations including:
  - Zimbabwe (ZW/USD)
  - Ghana (GH/GHS)
  - Nigeria (NG/NGN)
  - Mozambique (MZ/MZN)
  - Malawi (MW/MWK)
  - Kenya (KE/KES)

## Currency ID Mapping

Mukuru uses internal Currency IDs for its corridors. Based on our testing, these include:

- 18: ZAR to USD (Zimbabwe)
- 20: ZAR to GHS (Ghana) (example, may need verification)
- 21: ZAR to NGN (Nigeria) (example, may need verification)

## Test Script

The integration includes a comprehensive test script (`tests.py`) that combines multiple test types:

1. **API Tests**: Direct testing of the Mukuru API endpoints
   - Countries API testing
   - Pricechecker API testing

2. **Factory Tests**: Testing the provider through the factory
   - Verifies supported countries
   - Tests exchange rates for specific corridors

3. **Quote Tests**: Testing the get_quote method
   - Tests quotes for various corridors with different parameters

Run the tests with:
```bash
# Run all tests
python3 apps/providers/mukuru/tests.py

# Run specific test types
python3 apps/providers/mukuru/tests.py --api
python3 apps/providers/mukuru/tests.py --factory
python3 apps/providers/mukuru/tests.py --quote

# Run all tests explicitly
python3 apps/providers/mukuru/tests.py --all
```

## Implementation Details

The integration is implemented through the `MukuruProvider` class, which extends the base `RemittanceProvider`. The class handles:

- Fetching and caching supported countries from the Countries API
- Mapping currency IDs for different corridors
- Exchange rate calculation from the Pricechecker API
- Fee extraction from the Pricechecker API

## Key Methods

1. **get_supported_countries**: Fetches a list of supported recipient countries
   - Returns a dictionary mapping country codes to currency codes

2. **get_exchange_rate**: Fetches exchange rate information for a specific corridor
   - Returns a dictionary with exchange rate, fee, and receive amount
   - Handles unsupported corridors gracefully

3. **get_quote**: A convenience method that delegates to get_exchange_rate
   - Takes source currency and target country as parameters
   - Infers the sending country if not provided

## Implementation Notes

- The `get_quote` method handles cases where the sending country is not directly inferred from the currency code
- The implementation gracefully handles unsupported corridors by returning appropriate error messages
- The Countries API data is cached to reduce API calls
- The exchange rate is extracted from a string format like "$1:R18.7248"
- The fee is extracted from a string format like "ZAR94.00"
- The receive amount is extracted from a string format like "USD50.00"

## Current Limitations

1. The Currency ID mapping is based on limited testing and may need updates
2. Some corridors may not be supported or may return inaccurate information
3. The API formats could change, requiring updates to the parsing logic
4. We default to South Africa (ZA) as the sending country if not specified

## Notes

- The API is public and does not require authentication
- The rate string format is specific to each corridor and may need adjustments
- The implementation uses regular expressions to parse important values from strings
- The rate format "$1:R18.7248" means 1 USD = 18.7248 ZAR, so for ZAR to USD conversion, we use 1/18.7248 