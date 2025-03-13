# Western Union Provider Integration

## Overview

This module integrates Western Union's money transfer services directly into the RemitScout aggregator platform. The implementation connects to Western Union's pricing API to obtain real-time exchange rates, fees, and delivery options for various corridors worldwide.

## Features

- **Aggregator-Ready Design**: Fully compliant with the aggregator pattern, returning standardized responses
- **Real-Time Exchange Rates**: Connects directly to Western Union's pricing API
- **No Fallback Data**: Returns appropriate error messages when API calls fail, never falling back to mock data
- **Comprehensive Error Handling**: Detailed error messages for troubleshooting
- **Multiple Delivery Methods**: Supports various delivery options depending on the corridor
- **Fee Information**: Includes all fees in the response
- **Wide Currency Support**: Works with a broad range of currencies and corridors

## Usage

```python
from decimal import Decimal
from apps.providers.westernunion.integration import WesternUnionProvider

# Create a provider instance
provider = WesternUnionProvider()

# Get a quote
result = provider.get_quote(
    amount=Decimal("1000"),
    source_currency="USD",
    destination_currency="MXN",  # Optional, will be auto-detected based on country
    source_country="US",
    destination_country="MX"
)

# Check if the quote was successful
if result["success"]:
    print(f"Exchange rate: {result['exchange_rate']}")
    print(f"Fee: {result['fee']}")
    print(f"Destination amount: {result['destination_amount']} {result['destination_currency']}")
else:
    print(f"Error: {result['error_message']}")
```

## Response Format

### Success Response

```json
{
    "provider_id": "Western Union",
    "success": true,
    "error_message": null,
    "send_amount": 1000.0,
    "source_currency": "USD",
    "destination_amount": 20310.0,
    "destination_currency": "MXN",
    "exchange_rate": 20.3094,
    "fee": 0.0,
    "payment_method": "bankAccount",
    "delivery_method": "bankDeposit",
    "delivery_time_minutes": 1440,
    "timestamp": "2025-03-07T15:55:26.654908+00:00"
}
```

### Error Response

```json
{
    "provider_id": "Western Union",
    "success": false,
    "error_message": "Unsupported destination country: ZZ"
}
```

## Supported Functionality

- **Send Amount Quotes**: Get exchange rates based on a specific send amount
- **Multiple Corridors**: Supports a wide range of country-to-country transfers
- **Error Handling**: Standardized error messages for unsupported corridors, invalid parameters, and API failures

## Testing

The integration includes a comprehensive test script (`test_aggregator_integration.py`) that verifies functionality across multiple corridors. To run tests:

```bash
python3 apps/providers/westernunion/test_aggregator_integration.py [--debug] [--corridor INDEX] [--sleep SECONDS]
```

## Implementation Details

The implementation uses a sessionized approach to interact with Western Union's API:

1. **Session Initialization**: Establishes a session with proper cookies and headers
2. **Preflight Request**: Performs necessary CORS preflight requests
3. **Catalog Request**: Makes the main API call to get pricing data
4. **Response Parsing**: Extracts and standardizes the response data
5. **Error Handling**: Provides clear error messages when things go wrong

### Key API Interactions

- Initial GET to `/us/en/web/send-money/start` to obtain session cookies
- OPTIONS preflight request for CORS
- POST to `/wuconnect/prices/catalog` with sender and receiver details

## Limitations

- **Receive Amount Calculation**: Currently only supports send amount quotes, not receive amount
- **Delivery Method Selection**: Uses a default delivery method (bank deposit)
- **Payment Method Selection**: Uses a default payment method (bank account)
- **Country Coverage**: While many countries are supported, some may require additional mappings 