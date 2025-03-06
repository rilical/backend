# WireBarley Provider Integration

This module provides integration with the WireBarley remittance service API, supporting multiple currency corridors, exchange rates, and fee calculations.

## Authentication

The WireBarley API requires browser-like requests with valid session cookies. This integration supports two authentication methods:

### 1. Direct Cookie Injection (Preferred Method)

Use this method to directly inject cookies from an authenticated browser session:

1. Log in to WireBarley in your browser
2. Extract cookies using browser DevTools or a cookie manager extension
3. Set the following environment variables:

```bash
# Required: JSON string of cookie name/value pairs
export WIREBARLEY_COOKIES='{
    "_ga": "GA1.2.123456789.1234567890",
    "_fbp": "fb.1.1234567890.123456789",
    ...
}'

# Optional: Browser User-Agent to use
export WIREBARLEY_USER_AGENT="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)..."
```

### 2. Selenium Automation (Fallback Method)

If cookie injection is not used, the integration will fall back to automating the login process with Selenium:

```bash
# Required for Selenium automation
export WIREBARLEY_EMAIL="your.email@example.com"
export WIREBARLEY_PASSWORD="your_password"
```

## Usage Example

```python
from decimal import Decimal
from apps.providers.wirebarley import WireBarleyProvider

# Initialize provider
provider = WireBarleyProvider()

# Get available corridors
corridors = provider.get_corridors("USD")

# Get exchange rate for USD to PHP
rate = provider.get_exchange_rate(
    send_amount=Decimal("100"),
    send_currency="USD",
    receive_country="PH"
)

# Get a quote
quote = provider.get_quote(
    send_amount=100,
    send_currency="USD",
    receive_currency="PHP"
)
```

## Cookie Management

- Session cookies typically expire after some time (usually a few hours)
- For production use, implement a strategy to refresh cookies periodically
- Consider using a browser automation service if you need 24/7 operation

## Error Handling

Common error scenarios:

- `400 Bad Request`: Invalid or expired cookies
- `403 Forbidden`: Authentication failed
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server-side error

The integration includes automatic retry logic and session refresh on authentication errors.

## Fee Structure

WireBarley uses a complex fee structure with multiple components:

1. **Payment Method Fees**:
   - Each payment method (e.g., CREDIT_CARD, BANK_TRANSFER) has its own fee structure
   - Fees are tiered based on send amount thresholds
   - Some tiers may have discount fees available
   - Example structure:
     ```json
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
     ```json
     {
       "threshold": 500,
       "wbRate": 32.0332162,
       "threshold1": 1000,
       "wbRate1": 32.0494109
     }
     ```

## Rate Thresholds

The provider automatically handles threshold-based rates:

```python
# Get quote with amount-based threshold rate
quote = provider.get_quote(5000, 'USD', 'PHP')
if quote['success']:
    print(f"Rate for large amount: {quote['rate']}")

# Compare with smaller amount
small_quote = provider.get_quote(100, 'USD', 'PHP')
if small_quote['success']:
    print(f"Rate for small amount: {small_quote['rate']}")
```

## Debugging

Enable debug logging to see detailed request/response information:

```python
import logging
logging.getLogger('apps.providers.wirebarley').setLevel(logging.DEBUG)
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

## Supported Currencies

The integration supports multiple source currencies including:
- USD (United States Dollar)
- EUR (Euro)
- GBP (British Pound)
- AUD (Australian Dollar)
- CAD (Canadian Dollar)
- and many others

See the `CURRENCY_TO_COUNTRY` mapping in `integration.py` for a complete list.

## Testing

To run comprehensive tests:

```bash
python3 test_comprehensive.py
```

To test specific functionality:

```bash
python3 test_wirebarley_cli.py --exchange-rate --source-currency USD --target-country PH --amount 100
python3 test_wirebarley_cli.py --quote --source-currency USD --target-currency PHP --amount 500
python3 test_wirebarley_cli.py --corridors
```

### Browser Session Testing

For full testing with real data:

1. In Chrome/Firefox/Safari, visit wirebarley.com
2. Open Developer Tools and go to the Network tab
3. Look for requests to endpoints like `/my/remittance/api/v1/exrate/US/USD`
4. Copy the cookie values from the request headers
5. Add these cookie values to the session in `integration.py`

## Troubleshooting

Common issues:

1. **400 Errors**: Missing or invalid session cookies from a logged-in browser session
2. **Unsupported Currency**: Verify that both source and target currencies are supported
3. **Amount Range Issues**: Make sure the amount is within the supported range (typically 10-10000)

## Last Updated

March 3, 2025 