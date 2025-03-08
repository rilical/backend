# OrbitRemit Integration

## Overview

This module provides integration with OrbitRemit, a remittance service provider specializing in international money transfers primarily from Australia, New Zealand, UK, Europe, Canada, and the USA to various countries in Asia and the Pacific. The implementation allows fetching of exchange rates, fees, and quotes for supported corridors.

## API Details

The integration uses several API endpoints from OrbitRemit's services:

1. **Rates API**: `https://www.orbitremit.com/api/rates`
   - Purpose: Fetch current exchange rates
   - Method: GET
   - Authentication: None (public API)

2. **Fees API**: `https://www.orbitremit.com/api/fees`
   - Purpose: Get fee information for money transfers
   - Method: GET
   - Parameters: send_currency, payout_currency, amount

3. **Historic Rates API**: `https://www.orbitremit.com/api/historic-rates`
   - Purpose: Get historical exchange rate data
   - Method: GET
   - Parameters: send_currency, payout_currency, timescale

## Supported Corridors

OrbitRemit supports the following currency corridors:

| Source Currency | Destination Currencies |
|-----------------|------------------------|
| AUD (Australia) | PHP, INR, PKR, BDT, FJD, LKR, NPR, USD, VND |
| NZD (New Zealand) | PHP, INR, FJD, PKR, BDT, LKR, NPR, VND |
| GBP (United Kingdom) | PHP, INR, PKR, BDT, LKR, NPR, VND |
| EUR (Europe) | PHP, INR, PKR, BDT, LKR, NPR, VND |
| CAD (Canada) | PHP, INR, PKR, BDT, LKR, NPR, VND |
| USD (United States) | PHP, INR, PKR, BDT, LKR, NPR, VND |

Destination countries include:
- Philippines (PHP)
- India (INR)
- Pakistan (PKR)
- Bangladesh (BDT)
- Fiji (FJD)
- Sri Lanka (LKR)
- Nepal (NPR)
- Vietnam (VND)
- United States (USD)

## Implementation Details

The integration is implemented through the `OrbitRemitProvider` class, which extends the base `RemittanceProvider`. The implementation includes:

- API connection handling and error management
- Currency and country code mappings
- Exchange rate retrieval and fee calculation
- Standardized response formatting for the aggregator system

## Key Methods

1. **get_quote**: Fetches a detailed quote for a money transfer
   ```python
   result = provider.get_quote(
       amount=Decimal("1000"),
       source_currency="AUD",
       dest_country="IN"
   )
   ```

2. **get_exchange_rate**: Gets exchange rate information for a corridor
   ```python
   result = provider.get_exchange_rate(
       source_currency="AUD",
       target_currency="INR",
       amount=Decimal("1000")
   )
   ```

3. **get_fee_info**: Gets fee information for a specific transfer
   ```python
   result = provider.get_fee_info(
       send_currency="AUD",
       payout_currency="INR",
       send_amount=Decimal("1000"),
       recipient_type="bank_account"
   )
   ```

4. **get_historic_rates**: Retrieves historical exchange rate data
   ```python
   result = provider.get_historic_rates(
       send_currency="AUD",
       payout_currency="INR",
       timescale="weekly"
   )
   ```

## Response Format

The provider returns responses in a standardized format for the aggregator:

```json
{
  "provider_id": "orbitremit",
  "success": true,
  "error_message": null,
  "send_amount": 1000.0,
  "source_currency": "AUD",
  "destination_amount": 55200.0,
  "destination_currency": "INR",
  "exchange_rate": 55.2,
  "fee": 5.0,
  "payment_method": "BANK_TRANSFER",
  "delivery_method": "BANK_DEPOSIT",
  "delivery_time_minutes": 1440,
  "timestamp": "2025-03-08T06:48:50.123456Z"
}
```

## Error Handling

The integration includes comprehensive error handling with custom exceptions:

- `OrbitRemitError`: Base exception for all OrbitRemit-related errors
- `OrbitRemitConnectionError`: Network or connection issues
- `OrbitRemitApiError`: API-specific errors (invalid parameters, etc.)
- `OrbitRemitResponseError`: Issues with parsing or unexpected responses
- `OrbitRemitCorridorUnsupportedError`: Requested corridor is not supported

## Usage Example

```python
from decimal import Decimal
from apps.providers.orbitremit import OrbitRemitProvider

# Initialize provider
provider = OrbitRemitProvider()

# Get exchange rate
rate_info = provider.get_exchange_rate(
    source_currency="AUD",
    target_currency="PHP",
    amount=Decimal("1000")
)

# Get quote with full details
quote = provider.get_quote(
    amount=Decimal("1000"),
    source_currency="AUD",
    dest_country="PH"
)

# Check if successful
if quote["success"]:
    print(f"Exchange rate: {quote['exchange_rate']}")
    print(f"Fee: {quote['fee']}")
    print(f"Recipient gets: {quote['destination_amount']} {quote['destination_currency']}")
else:
    print(f"Error: {quote['error_message']}")
```

## Notes

- OrbitRemit primarily focuses on transfers from developed countries to specific Asian and Pacific destinations
- The API is public and does not require authentication tokens
- Exchange rates and fees may vary based on the amount being sent
- The service provides both bank transfer and cash pickup options in some corridors
- Transfer times are typically 1-3 business days 