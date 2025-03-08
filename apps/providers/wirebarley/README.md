# WireBarley Provider Integration

## Overview

This module integrates the WireBarley international money transfer service into the RemitScout platform with an aggregator-ready implementation that provides standardized responses with no fallback data.

## Features

- **Real-time Exchange Rates**: Fetch live exchange rates from WireBarley's API
- **Fee Calculation**: Calculate fees based on transfer amount and corridor
- **Multiple Corridors**: Support for a wide range of currency corridors
- **Threshold-Based Rates**: Handling of WireBarley's tiered exchange rates based on transfer amount
- **Session Management**: Automatic session management using cookie-based or Selenium-based authentication
- **Standardized Responses**: Returns standardized responses in the aggregator format
- **No Fallback Data**: Returns `"success": false` if API calls fail without fallback to mock data

## Implementation

The implementation in `integration.py` is an aggregator-ready integration that provides standardized responses for the money transfer aggregator platform.

```python
from apps.providers.wirebarley.integration import WireBarleyProvider
from decimal import Decimal

# Initialize provider
provider = WireBarleyProvider()

# Get quote
result = provider.get_quote(
    amount=Decimal("500.00"),
    source_currency="USD", 
    destination_currency="PHP"
)

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
    "provider_id": "wirebarley",
    "success": true,
    "error_message": null,
    "send_amount": 500.0,
    "source_currency": "USD",
    "destination_amount": 27895.5,
    "destination_currency": "PHP",
    "exchange_rate": 55.791,
    "fee": 4.99,
    "payment_method": "bankAccount",
    "delivery_method": "bankDeposit",
    "delivery_time_minutes": 1440,
    "timestamp": "2025-03-07T16:25:30.654908+00:00"
}
```

### Error Response

```json
{
    "provider_id": "wirebarley",
    "success": false,
    "error_message": "Unsupported receive currency: XYZ"
}
```

## Authentication

The integration supports two methods of authentication:

1. **Direct Cookie Injection** (preferred)
   - Set `WIREBARLEY_COOKIES` environment variable with a JSON string of cookie name/value pairs
   - Optionally set `WIREBARLEY_USER_AGENT` to specify the User-Agent header

2. **Selenium Automation** (fallback)
   - Set `WIREBARLEY_EMAIL` and `WIREBARLEY_PASSWORD` environment variables
   - The implementation will use Selenium to automate login and extract cookies

Example `WIREBARLEY_COOKIES` format:
```json
{
    "_ga": "GA1.2.123456789.1234567890",
    "_fbp": "fb.1.1234567890.123456789",
    "auth_token": "your-auth-token"
}
```

## Testing

Use the test script to verify the implementation:

```bash
python apps/providers/wirebarley/test_aggregator.py --debug
```

Or test a specific corridor:

```bash
python apps/providers/wirebarley/test_aggregator.py --corridor USD-PHP
```

## Supported Corridors

The implementation supports a wide range of currency corridors, including:

- USD to PHP, INR, KRW, CNY, etc.
- EUR to various currencies
- GBP to various currencies
- And many more

Check the `CURRENCY_TO_COUNTRY` mapping in the code for the full list of supported currencies.

## Error Handling

The implementation handles errors by returning a standardized response with:
- `"success": false`
- `"error_message"` describing the issue (no fallback to mock data)

Common error cases include:
- Invalid/unsupported currencies
- Amount outside allowed range
- API errors from WireBarley
- Authentication failures
- Session expiration

## Implementation Details

### Key Components

1. **Session Management**
   - Handles cookie-based or Selenium-based authentication
   - Session validation and automatic renewal

2. **API Interaction**
   - Handles API requests with proper headers and cookies
   - Parses response data and extracts rates/fees

3. **Threshold-Based Rates**
   - Logic to determine the correct rate based on amount thresholds
   - Handles WireBarley's tiered pricing structure

4. **Fee Calculation**
   - Determines fees based on payment methods and amount tiers
   - Handles discount fees when available

5. **Standardized Response Formatting**
   - Converts WireBarley-specific data to standardized aggregator format
   - Ensures consistent response structure for both success and error cases

## Fee Structure

WireBarley uses a complex fee structure with multiple components:

1. **Payment Method Fees**:
   - Each payment method (e.g., CREDIT_CARD, BANK_TRANSFER) has its own fee structure
   - Fees are tiered based on send amount thresholds
   - Some tiers may have discount fees available
   - Example structure:
     ```
     {
       "useDiscountFee": false,
       "min": 10,
       "fee1": 4.99,
       "discountFee1": null,
       "threshold1": 500.01,
       "fee2": 5.99,
       "max": 2999,
       "option": "CREDIT_DEBIT_CARD"
     }
     ```

2. **Transfer Method Fees**:
   - Additional fees based on the transfer/payout method
   - May vary by corridor and amount
   - Usually simpler structure than payment fees

3. **Threshold-Based Exchange Rates**:
   - Exchange rates can vary based on send amount
   - Higher amounts may get preferential rates
   - Example structure:
     ```
     {
       "threshold": 500,
       "wbRate": 32.0332162,
       "threshold1": 1000,
       "wbRate1": 32.0494109
     }
     ```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `WIREBARLEY_COOKIES` | No* | JSON string of browser cookies |
| `WIREBARLEY_USER_AGENT` | No | Browser User-Agent string |
| `WIREBARLEY_EMAIL` | No* | Login email (for Selenium) |
| `WIREBARLEY_PASSWORD` | No* | Login password (for Selenium) |

\* Either `WIREBARLEY_COOKIES` or both `WIREBARLEY_EMAIL` and `WIREBARLEY_PASSWORD` must be provided.

## Development Notes

- The integration uses requests for API calls and Selenium for login automation
- Cookie-based authentication is more efficient than Selenium automation
- Consider implementing a cookie refresh mechanism for long-running applications
- The implementation adheres to the standard aggregator pattern for consistent response formats

## Last Updated

March 8, 2025 