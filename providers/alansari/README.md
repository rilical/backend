# Al Ansari Exchange Provider Integration

This directory contains the production‐ready integration for **Al Ansari Exchange**, a major UAE‐based money transfer provider. It implements:

- **Live exchange rate** lookups for multiple corridors:
  - By default, **AED** as source currency (UAE) to various countries (IN, PK, PH, BD, etc.).
- **Automatic security token** fetching and refreshing:
  - The provider extracts the security token from Al Ansari's homepage HTML.
  - It uses that token for subsequent requests to the AJAX API.
  - The token is extracted from the JavaScript in the page.

## Main Class

The provider class is [`AlAnsariProvider`](./integration.py), which inherits from our [`RemittanceProvider`](../base/provider.py). It:

- **Implements** the `get_quote(...)` method that returns a standardized JSON/dict structure (with keys like `success`, `exchange_rate`, `fee`, etc.).
- **Relies** on an internal `_setup_session` for shared session/headers.
- **Uses** `fetch_security_token` to automatically extract the security token from the website.

## Example Usage

```python
from decimal import Decimal
from apps.providers.alansari.integration import AlAnsariProvider

provider = AlAnsariProvider()

quote = provider.get_quote(
    amount=Decimal("1000.00"),
    source_currency="AED",
    dest_currency="INR",
    source_country="UNITED ARAB EMIRATES",  # or "AE"
    dest_country="INDIA",                  # or "IN"
    payment_method="cash",
    delivery_method="cash",
    include_raw=True   # to see the raw API response
)

print("Success:", quote["success"])
print("Exchange Rate:", quote["exchange_rate"])
print("Receive Amount:", quote["destination_amount"], quote["destination_currency"])
print("Fee:", quote["fee"])
```
The result is always standardized, e.g.:
```
{
  "provider_id": "alansari",
  "success": true,
  "error_message": null,
  "send_amount": 1000.0,
  "source_currency": "AED",
  "destination_amount": 22500.0,
  "destination_currency": "INR",
  "exchange_rate": 22.5,
  "fee": 0.0,
  "payment_method": "cash",
  "delivery_method": "cash",
  "delivery_time_minutes": 60,
  "timestamp": "2025-03-05T19:46:28.884539",
  "raw_response": {
    "amount": "22500.000",
    "get_rate": "22.5000",
    "status_msg": "SUCCESS"
  }
}
```

## Running Tests

A single tests.py file contains all relevant test logic. To run:
```
cd apps/providers/alansari
python tests.py
```
It will:
- Create an AlAnsariProvider instance.
- Auto‐fetch the security token from the website.
- Call the get_quote method with sample corridors.
- Verify results in a unified test style.

## Known Limitations

- In production, you must confirm corridor support. If a currency/country is not in Al Ansari's system, get_quote returns "success": false.
- The security token is extracted from the website HTML.
- Zero or negative amounts will fail validation.
- The API sometimes returns HTTP 400 errors, which may indicate API rate limiting.

## Features

- Exchange rate lookup for multiple currency corridors
- Support for remittances from UAE to various countries
- Real-time API integration with Al Ansari Exchange's public API
- Automatic security token extraction from the website
- Comprehensive error handling and logging

## Supported Corridors

The integration is designed to support a wide range of corridors, with UAE (AED) as the primary source currency:

### Source Country
- United Arab Emirates (AED)

### Major Destination Countries/Currencies
- India (INR)
- Pakistan (PKR)
- Philippines (PHP)
- Bangladesh (BDT)
- Sri Lanka (LKR)
- Nepal (NPR)
- Egypt (EGP)
- And many more (see the CURRENCY_ID_MAPPING in integration.py)

## Implementation Details

The core of the integration is the `AlAnsariProvider` class in `integration.py`, which handles all interactions with the Al Ansari Exchange website and API.

### API Integration

The provider uses Al Ansari Exchange's AJAX endpoint:
```
POST https://alansariexchange.com/wp-admin/admin-ajax.php
```

Key parameters for exchange rate lookup:
- `action`: "convert_action"
- `currfrom`: Currency ID from which to convert (e.g., "91" for AED)
- `currto`: Currency ID to which to convert (e.g., "27" for INR)
- `cntcode`: Country code for the destination currency
- `amt`: Amount to convert
- `security`: Security token (dynamically extracted from website)
- `trtype`: Transaction type (e.g., "BT" for Bank Transfer)

### Security Token Retrieval

A critical aspect of the Al Ansari API integration is the security token. The provider automatically:

1. Fetches the Al Ansari Exchange website homepage
2. Extracts the security token using regex pattern matching
3. Finds the token in the JavaScript section of the HTML (`ajax_nonce` parameter)
4. Uses the token for subsequent API calls

### Currency and Country Mapping

The integration includes comprehensive mappings between:
- ISO currency codes (e.g., "INR") and Al Ansari internal currency IDs (e.g., "27")
- Standard country names and Al Ansari internal country IDs

## Testing

The provider includes test modules for verifying integration functionality:
- `tests.py`: Comprehensive test suite with direct API tests for various corridors and error conditions

### Running Tests

Tests can be run with:

```
cd backend
PYTHONPATH=/path/to/backend python3 apps/providers/alansari/tests.py
```

## Error Handling

The integration includes comprehensive error handling:

- `AlAnsariError`: Base exception for all Al Ansari-related errors
- `AlAnsariAuthError`: Authentication failures
- `AlAnsariConnectionError`: Network connection issues
- `AlAnsariValidationError`: Invalid input parameters
- `AlAnsariApiError`: API-specific errors
- `AlAnsariResponseError`: Error parsing API response
- `AlAnsariCorridorUnsupportedError`: Requested corridor is not supported
- `AlAnsariSecurityTokenError`: Security token issues

## Example API Response

The provider returns a standardized response similar to:

```json
{
  "provider_id": "alansari",
  "success": true,
  "send_amount": 1000.0,
  "source_currency": "AED",
  "destination_amount": 22451.0,
  "destination_currency": "INR",
  "exchange_rate": 22.451,
  "fee": 0.0,
  "delivery_time_minutes": 1440,
  "error_message": null,
  "timestamp": "2025-03-05T23:57:27.579240",
  "raw_response": {
    "status_msg": "SUCCESS",
    "amount": "22451.000",
    "get_rate": "22.451"
  }
}
``` 