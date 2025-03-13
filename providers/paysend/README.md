# Paysend Provider Integration

This package implements a RemitScout integration with [Paysend](https://paysend.com), a global money transfer service offering competitive rates for international remittances. The integration works by accessing Paysend's public quote API to fetch real-time exchange rates and fees.

## Overview

Paysend is known for its:
- Digital-first approach to money transfers
- Competitive exchange rates
- Fast transfers (often within minutes)
- Support for 100+ countries
- Multiple payout methods including bank deposits, mobile wallets, and cash pickup

## Implementation

The integration is designed to mimic a web browser session to fetch quotes from Paysend's public API. It uses the following approach:

1. Initializes a session with browser-like headers and cookies
2. Accesses Paysend's quote API endpoint with appropriate parameters
3. Processes the response to extract rates, fees, and other transaction details
4. Returns standardized data for comparison with other providers

## Usage

Basic usage example:

```python
from decimal import Decimal
from apps.providers.paysend import PaysendProvider

# Initialize the provider
provider = PaysendProvider()

# Get an exchange rate quote
result = provider.get_exchange_rate(
    send_amount=Decimal("1000.00"),
    send_currency="USD",
    receive_country="IN",
    receive_currency="INR"
)

print(f"Exchange rate: {result['exchange_rate']}")
print(f"Fee: {result['fee']}")
print(f"Recipient gets: {result['destination_amount']} {result['destination_currency']}")
```

## API Endpoints

The main endpoints used by this integration are:

- **Quote API**: `/api/public/quote` - Gets exchange rate information for a specific amount and corridor

## Configuration Options

When initializing the provider, you can customize the following parameters:

- `user_agent`: Custom User-Agent string to use (defaults to a Safari-like user agent)
- `timeout`: Request timeout in seconds (defaults to 30)

Example with custom parameters:

```python
provider = PaysendProvider(
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    timeout=15
)
```

## Error Handling

The integration includes comprehensive error handling for:

- Network errors and timeouts
- Authentication failures
- Rate limiting
- Invalid parameters
- API errors

Each error type raises a specific exception that extends the base `PaysendError`.

## Notes

- This integration relies on Paysend's public web API, which might change without notice.
- The actual API endpoints and parameters might differ from what is implemented here.
- You should monitor the integration regularly and update it if Paysend changes their API.
- This implementation assumes that the quote endpoint is `/api/public/quote`, but you should verify this with actual network logs.

## Testing

To test this integration, run:

```bash
pytest apps/providers/paysend/tests.py -v
``` 