# RemitGuru Provider

An aggregator-ready implementation of RemitGuru's money transfer service API.

> **IMPORTANT**: RemitGuru currently only supports money transfers from United Kingdom (GBP) to India (INR). All other corridors will return appropriate error responses.

## Features

- **Live API Integration**: Fetches real-time quotes and exchange rates from RemitGuru's public API.
- **Standardized Response Format**: Follows the aggregator's standard format for consistent integration.
- **No Mock Data**: Returns proper error responses instead of fallback data for unsupported corridors.
- **Corridor Validation**: Validates transfer corridors before making API requests.
- **Error Handling**: Comprehensive error handling with meaningful error messages.

## Supported Corridors

RemitGuru's API has been extensively tested and currently only supports:

- United Kingdom (GBP) → India (INR)

All other corridors will return error responses with appropriate messages.

## Usage

### Basic Usage

```python
from decimal import Decimal
from apps.providers.remitguru.integration import RemitGuruProvider

# Create provider instance
with RemitGuruProvider() as provider:
    # Get a quote for the only supported corridor (GB → IN)
    quote = provider.get_quote(
        amount=Decimal("500"),
        source_currency="GBP",
        dest_currency="INR",
        source_country="GB",
        dest_country="IN"
    )
    
    print(quote)
```

### Response Format

Successful response:

```python
{
    "provider_id": "remitguru",
    "success": True,
    "error_message": None,
    "send_amount": 500.0,
    "source_currency": "GBP",
    "destination_amount": 51995.0,
    "destination_currency": "INR",
    "exchange_rate": 103.99,
    "fee": 0.0,
    "payment_method": "bank",
    "delivery_method": "bank",
    "delivery_time_minutes": 1440,
    "timestamp": "2025-03-06T21:53:36.133712"
}
```

Error response:

```python
{
    "provider_id": "remitguru",
    "success": False,
    "error_message": "Fee Not Define.",  # Error message from RemitGuru API
    "send_amount": 500.0,
    "source_currency": "USD",
    "destination_amount": 0.0,
    "destination_currency": "PKR",
    "exchange_rate": None,
    "fee": 0.0,
    "payment_method": "bank",
    "delivery_method": "bank",
    "delivery_time_minutes": 1440,
    "timestamp": "2025-03-06T21:53:36.440556"
}
```

## Implementation Details

### Country and Currency Mapping

The provider includes mappings for countries and currencies:

- `CORRIDOR_MAPPING`: Maps standard ISO country codes to RemitGuru's format (mostly the same)
- `CURRENCY_MAPPING`: Maps country codes to their default currencies
- `SUPPORTED_CORRIDORS`: List of corridors known to work properly

### API Endpoints

- Base URL: `https://www.remitguru.com`
- Quote Endpoint: `/transfer/jsp/getQTStatistics.jsp`
- Methods: Primarily POST requests for quotes

## Testing

To test the provider, run:

```bash
python -m apps.providers.remitguru.test_provider
```

This runs a comprehensive test suite that:
1. Tests quotes for supported and unsupported corridors
2. Verifies the exchange rate functionality
3. Lists supported countries and currencies

## Error Cases Handled

1. Unsupported corridors
2. API connection failures
3. Malformed API responses
4. Unsupported currencies
5. Validation errors

## Integration with the Aggregator

This provider follows the aggregator's standardized format for easy integration into the comparison engine. It implements the abstract methods required by the `RemittanceProvider` base class:

- `get_quote()`: Get a standardized quote for a specific corridor
- `get_exchange_rate()`: Legacy method for backward compatibility
- `get_supported_countries()`: List countries in ISO alpha-2 format
- `get_supported_currencies()`: List supported currencies in ISO format 