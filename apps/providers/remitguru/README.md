# RemitGuru Integration

This directory contains the integration with RemitGuru's API for fetching exchange rates and fees for international money transfers.

## Overview

RemitGuru is an international money transfer service that offers competitive exchange rates for various corridors. This integration allows us to fetch live exchange rates and fees for money transfers.

## API Details

The RemitGuru integration uses the following API endpoint:

- Exchange Rate Endpoint: `https://www.remitguru.com/transfer/jsp/getQTStatistics.jsp`
  - Method: `POST`
  - Content-Type: `application/x-www-form-urlencoded`

### Request Parameters

| Parameter       | Description                                                |
|-----------------|------------------------------------------------------------|
| amountTransfer  | Amount to send (in integer format)                         |
| corridor        | Format: `{FROM_COUNTRY}~{FROM_CURRENCY}~{TO_COUNTRY}~{TO_CURRENCY}` |
| sendMode        | Default is "CIP-FER"                                       |

### Response Format

The API returns a pipe-delimited string with the following format:

```
receive_amount|exchange_rate|fee|send_amount|error_message|is_valid|send_currency|error_code
```

Example valid response:
```
811902.00|104.09|0.00|7800.00||true|GBP|
```

Example error response:
```
0.00|0.00|0.00|1000.00|Fee Not Define.|false|GBP|FBERR1001
```

## Supported Corridors

Based on our testing, the following corridors are currently confirmed to be supported by RemitGuru:

- GBP to INR (United Kingdom to India)

Other corridors we tested returned "Fee Not Define" errors.

## Implementation Details

The implementation is in the `integration.py` file, which includes:

1. `RemitGuruProvider` class that extends the base `RemittanceProvider`
2. Methods for getting exchange rates and other information
3. Error handling and logging

### Key Methods

- `get_exchange_rate`: Main method to fetch exchange rates for a given corridor
- `get_quote`: Internal method that makes the actual API request
- `get_supported_countries`: Returns a list of supported corridors

## Testing

The integration includes a test script (`test_remitguru.py`) that tests the functionality with various corridors.

To run the test:

```bash
python3 apps/providers/remitguru/test_remitguru.py
```

## Notes

- The API requires cookies from the homepage, so a visit to the homepage is made first to get the necessary cookies.
- The API may return error messages for unsupported corridors or invalid requests.
- Rate limits and other restrictions may apply to the API. 