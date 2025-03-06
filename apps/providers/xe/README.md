# XE Money Transfer Integration

## Overview

This module provides integration with XE Money Transfer, an international money transfer service that offers competitive exchange rates through a white-label partnership with Ria Money Transfer. The implementation allows fetching of exchange rates, fees, and supported corridors.

## API Details

The integration uses two main API endpoints:

1. **Mid-market Rates API**: `https://www.xe.com/api/protected/midmarket-converter/`
   - Purpose: Fetch current mid-market exchange rates
   - Method: GET
   - Authentication: None (public API)

2. **Quotes API**: `https://launchpad-api.xe.com/v2/quotes`
   - Purpose: Get money transfer quotes with fees and delivery times
   - Method: POST
   - Content-Type: application/json
   - Required Headers:
     - `X-Correlation-ID`: Unique ID in format `XECOM-{uuid}`
     - `deviceid`: UUID representing the device

## Request Parameters

Key parameters for the quotes API:

| Parameter | Description |
|-----------|-------------|
| sellCcy | The currency to send (e.g., "USD") |
| buyCcy | The currency to receive (e.g., "INR") |
| userCountry | Country code for sender (e.g., "US") |
| amount | Amount to send (numeric) |
| fixedCcy | Which currency is fixed (usually the send currency) |
| countryTo | Destination country code (e.g., "IN") |

## Response Format

The API returns detailed quote information including:

- Exchange rate
- Transfer fees
- Payment method options
- Delivery methods
- Estimated delivery times
- Total cost including fees

Example successful quote response structure:
```json
{
  "quote": {
    "buyCcy": "INR",
    "sellCcy": "USD",
    "individualQuotes": [
      {
        "settlementMethod": "DirectDebit",
        "deliveryMethod": "BankAccount",
        "isDefault": true,
        "rate": 87.0505,
        "buyAmount": "43,525.24",
        "transferFee": "3.00",
        "leadTime": "3 business days"
      }
    ]
  }
}
```

## Supported Corridors

Based on testing, the following corridors are supported:

- USD to INR (United States to India)
- GBP to PHP (United Kingdom to Philippines)
- CAD to MXN (Canada to Mexico)
- GBP to INR (United Kingdom to India)

Each corridor provides multiple delivery and payment method options with different fees and delivery times.

## Implementation Details

The integration is implemented through the `XEProvider` class, which extends the base `RemittanceProvider`. The class handles:

- Authentication and header management
- Currency and country code mappings
- Quote request formatting
- Response parsing
- Error handling

## Key Methods

1. **get_quote**: Fetches a detailed quote for a money transfer
   - Handles currency conversion, fees, and delivery times
   - Returns a Quote object with all details

2. **get_exchange_rate**: Gets exchange rate information for a corridor
   - Returns a dictionary with exchange rate, fee, and receive amount
   - Handles unsupported corridors gracefully

3. **get_supported_countries**: Returns a list of supported destination countries
   - Each country includes code, name, and currency

## Testing

A test script (`test_xe.py`) is provided to test:
1. Mid-market rates API
2. Quotes API for various corridors
3. Exchange rates for different corridors

Run the tests with:
```
python3 apps/providers/xe/test_xe.py
```

## Notes

- The API appears to be a front-end for Ria Money Transfer services
- No API key is required, but proper headers are needed
- Some warnings about minimum amounts appear for certain corridors
- Exchange rates include a margin over the mid-market rate
- The mid-market rates API returns a 401 error, indicating it may require authentication

## XE API Status Update (March 2025)

As of March 2025, we have identified some changes in the XE API services:

1. **Direct Quote API Working**: The direct quotes API endpoint (`https://launchpad-api.xe.com/v2/quotes`) is working correctly and returning valid data.

2. **XE Money Transfer Website Changes**: The previous XE Money Transfer website URLs (`https://www.xe.com/xemoneytransfer/send/`) are returning 404 errors, indicating a potential website restructuring.

3. **Mid-market Rates Endpoint Requires Authentication**: The midmarket rates endpoint now requires authentication and returns 401 Unauthorized without proper credentials.

The integration has been updated to better handle the current API response format from the quotes API. This includes:

- Improved parsing of response data, including handling of formatted string values
- Better extraction of rate, amount, and fee information
- Proper attribution of provider information (the actual provider is Ria, as indicated in the API response)
- Enhanced error handling for API issues

### Recent Testing Results

Testing with the direct quotes API has shown:

- Most currency corridors are successfully returning data through the quotes API
- Multiple payment and delivery methods are available in the response
- The API returns detailed information about fees, exchange rates, and delivery times

### Notes for Future Development

1. Consider implementing API authentication for the midmarket rates endpoint if needed
2. Regular monitoring of API endpoint changes needed as XE appears to be restructuring their services
3. The quotes API is returning information from the Ria provider, suggesting XE may be acting as an aggregator 