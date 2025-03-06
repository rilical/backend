# Dahabshiil Money Transfer Integration

## Overview

This module provides integration with Dahabshiil, an international money transfer service with a strong presence in East Africa and the Middle East. The integration allows fetching exchange rates, fees, and processing money transfer quotes for supported corridors.

## API Details

The integration uses the following API endpoint:

1. **Get Charges API**: `https://apigw-us.dahabshiil.com/remit/transaction/get-charges-anonymous`
   - Purpose: Get exchange rate, fee, and amount information for money transfers
   - Method: GET
   - Parameters:
     - `source_country_code`: Country code of sender (e.g., "US")
     - `destination_country_iso2`: Country code of receiver (e.g., "KE")
     - `amount_type`: "SOURCE" (for send amount) or "DESTINATION" (for receive amount)
     - `amount`: Amount to send/receive (e.g., "700.00")
     - `destination_currency`: Currency code to receive (e.g., "USD", "KES")
     - `type`: Payout method (e.g., "Cash Collection")
   - Authentication: None (public API)
   - Format: JSON
   - Status: **Working** - Returns exchange rate, fee, and amount information

## API Response Format

### Get Charges API

The Get Charges API returns data in the following format:

```json
{
  "status": "Success",
  "code": 200,
  "data": {
    "charges": {
      "source_currency": "USD",
      "source_amount": 700,
      "rate": 1,
      "base_rate": 1,
      "destination_currency": "USD",
      "destination_amount": 700,
      "commission": 42,
      "agent_fee": "0",
      "hq_fee": "0",
      "total_charges": 42,
      "tax": "0.00"
    }
  }
}
```

Where:
- `status`: Indicates if the request was successful
- `code`: HTTP status code
- `data.charges`: Contains detailed information about the transfer
  - `source_currency`: Currency code of the sending amount
  - `source_amount`: Amount being sent
  - `rate`: Exchange rate from source to destination currency
  - `destination_currency`: Currency code of the receiving amount
  - `destination_amount`: Amount being received
  - `commission`: Base fee for the transfer
  - `total_charges`: Total fee including all charges
  - `tax`: Any applicable taxes

## Supported Corridors

Based on our testing, Dahabshiil typically supports corridors from:

- United States (US/USD) to:
  - Kenya (KE/USD or KES)
  - Ethiopia (ET/ETB)
  - Somalia (SO/USD)
  - Uganda (UG/UGX)
  - Rwanda (RW/RWF)

- United Kingdom (GB/GBP) to:
  - Kenya (KE/USD or KES)
  - Somalia (SO/USD)
  - Ethiopia (ET/ETB)

## Test Script

The integration includes a comprehensive test script (`tests.py`) that combines multiple test types:

1. **API Tests**: Direct testing of the Dahabshiil API endpoints
   - Get Charges API testing

2. **Factory Tests**: Testing the provider through the factory
   - Verifies supported countries
   - Tests exchange rates for specific corridors

3. **Quote Tests**: Testing the get_quote method
   - Tests quotes for various corridors with different parameters

Run the tests with:
```bash
# Run all tests
python3 apps/providers/dahabshiil/tests.py --all

# Run specific test types
python3 apps/providers/dahabshiil/tests.py --api
python3 apps/providers/dahabshiil/tests.py --factory
python3 apps/providers/dahabshiil/tests.py --quote
```

## Implementation Details

The integration is implemented through the `DahabshiilProvider` class, which extends the base `RemittanceProvider`. The class handles:

- Mapping currency codes to country codes when necessary
- Exchange rate calculation from the Get Charges API
- Fee extraction from the Get Charges API

## Key Methods

1. **get_supported_countries**: Returns a list of supported destination countries
   - Currently returns a hardcoded list of likely supported countries

2. **get_exchange_rate**: Fetches exchange rate information for a specific corridor
   - Makes a request to the Get Charges API
   - Returns a dictionary with exchange rate, fee, and receive amount
   - Handles unsupported corridors gracefully

3. **get_quote**: A convenience method that delegates to get_exchange_rate
   - Takes source currency and target country as parameters
   - Infers the sending country if not provided

## Implementation Notes

- The `get_quote` method handles cases where the sending country is not directly inferred from the currency code
- The implementation gracefully handles unsupported corridors by returning appropriate error messages
- Default payout type is set to "Cash Collection"
- The provider infers the appropriate receive currency based on the destination country when not specified

## Current Limitations

1. The integration doesn't include all payout methods that Dahabshiil might support
2. Some corridors may not be supported or may return inaccurate information
3. The API formats could change, requiring updates to the parsing logic
4. We default to US as the sending country if not specified

## Notes

- The API is public and does not require authentication
- The rate value represents how many units of destination currency you get for 1 unit of source currency
- If Cloudflare protection is added in the future, the implementation may need to be updated with appropriate tokens 