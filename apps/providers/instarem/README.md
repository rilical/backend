# InstaRem Provider Integration

This module implements integration with InstaRem, a popular money transfer service known for competitive exchange rates, especially for Asian corridors.

## Features

- Exchange rate lookup for 61 money transfer corridors
- Support for 6 source countries and 20 destination countries
- Real-time API integration with InstaRem's public API
- Fallback mechanisms for cases where the API fails
- Comprehensive error handling and logging

## Supported Corridors

The integration supports a wide range of corridors, including but not limited to:

### Source Countries
- United States (USD)
- United Kingdom (GBP)
- Australia (AUD)
- Singapore (SGD)
- Hong Kong (HKD)
- Malaysia (MYR)

### Destination Countries
- India (INR)
- Philippines (PHP)
- Singapore (SGD)
- Malaysia (MYR)
- Australia (AUD)
- Hong Kong (HKD)
- Vietnam (VND)
- Indonesia (IDR)
- Thailand (THB)
- China (CNY)
- United Kingdom (GBP)
- And many more...

## Implementation Details

The core of the integration is the `InstaRemProvider` class in `integration.py`, which handles all interactions with the InstaRem API.

### API Integration

The provider uses InstaRem's public transaction computed-value endpoint:
```
GET https://www.instarem.com/api/v1/public/transaction/computed-value
```

Key parameters:
- `source_currency`: The currency to send (e.g., "USD")
- `destination_currency`: The currency to receive (e.g., "INR")
- `instarem_bank_account_id`: The bank account ID for the corridor (e.g., 58)
- `country_code`: The source country code (e.g., "US")
- `source_amount`: The amount to send

### Bank Account IDs

A critical aspect of the InstaRem API integration is the `instarem_bank_account_id` parameter. Through testing, we discovered that this parameter is required, but the values are not corridor-specific as previously thought.

Instead, each source country appears to use a single bank account ID for all destinations:
- US-based sending: ID 58
- UK-based sending: ID 81
- Australia-based sending: ID 90
- Singapore-based sending: ID 100
- Hong Kong-based sending: ID 109
- Malaysia-based sending: ID 116

### HTTP Headers

The implementation includes proper HTTP headers based on browser inspection to ensure successful API calls:

```python
headers = {
    "Accept": "*/*",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.instarem.com/en-us/",
    "X-Requested-With": "XMLHttpRequest"
}
```

## Fallback Mechanism

When the API call fails, the provider implements a fallback mechanism:

1. Uses a comprehensive dictionary of currency exchange rates
2. Applies a reasonable margin (typically 1.5%)
3. Estimates delivery times based on corridor data
4. Flags the response as a fallback for tracking

## Testing

The provider includes a comprehensive test script (`test_instarem.py`) to validate exchange rates and coverage.

Example test command:
```
python3 -m apps.providers.instarem.test_instarem --amount 1000 --currency USD --destinations "IN,PH,MY,SG"
```

## Debugging

For debugging API issues, a diagnostic script (`debug_test.py`) is provided that compares successful and fallback responses.

## Troubleshooting

If the API returns "Unknown API error", check:
1. The `instarem_bank_account_id` parameter values
2. HTTP headers
3. The structure of the request URL and parameters

## Example Usage

```python
from apps.providers.instarem.integration import InstaRemProvider
from decimal import Decimal

provider = InstaRemProvider()
result = provider.get_exchange_rate(
    send_amount=Decimal("1000.00"),
    send_currency="USD",
    receive_country="IN"
)
print(f"Exchange rate: {result['exchange_rate']}")
print(f"Fee: {result['fee']}")
print(f"Amount: {result['destination_amount']} {result['destination_currency']}")
provider.close()
```

## Error Handling

The integration includes comprehensive error handling:

- `InstaRemError`: Base exception for all InstaRem-related errors
- `InstaRemAuthenticationError`: Authentication failures
- `InstaRemConnectionError`: Network connection issues
- `InstaRemValidationError`: Invalid input parameters
- `InstaRemRateLimitError`: Rate limit exceeded
- `InstaRemApiError`: API-specific errors

---

## API Response Example

Below is an example of the standardized response from the provider:

```json
{
  "provider_id": "InstaRem",
  "source_currency": "USD",
  "source_amount": 1000.0,
  "destination_currency": "INR",
  "destination_amount": 83152.5,
  "exchange_rate": 83.1525,
  "fee": 0.0,
  "delivery_method": "Bank Deposit",
  "delivery_time_minutes": 60,
  "corridor": "US-IN",
  "payment_method": "Bank Transfer",
  "details": {
    "margin_amount": 112.5,
    "margin_percent": 0.75,
    "official_fx_rate": 83.75
  }
}
``` 