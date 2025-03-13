# Remitly Provider

An aggregator-ready implementation of Remitly's money transfer service API with no mock data fallbacks.

## Features

- **Live API Integration**: Fetches real-time quotes and exchange rates from Remitly's public API
- **Standardized Response Format**: Follows the aggregator's standard format for consistent integration
- **No Mock Data**: Returns proper error responses instead of fallback data for unsupported corridors or API errors
- **Error Handling**: Comprehensive error handling with retry logic for network issues and rate limiting
- **Wide Coverage**: Supports numerous currency pairs and countries offered by Remitly

## Supported Corridors

Remitly offers a wide range of corridors, primarily for sending money from:
- United States (USD)
- Canada (CAD)
- United Kingdom (GBP)
- Europe (EUR)
- Australia (AUD)

To destinations including:
- Philippines (PHP)
- India (INR)
- Mexico (MXN)
- Colombia (COP)
- And many more (see `get_supported_countries()` method)

## Usage

### Basic Usage

```python
from decimal import Decimal
from apps.providers.remitly.integration import RemitlyProvider

# Create provider instance
with RemitlyProvider() as provider:
    # Get a quote
    quote = provider.get_quote(
        amount=Decimal("500"),
        source_currency="USD",
        dest_currency="PHP",
        source_country="US",
        dest_country="PH"
    )
    
    print(quote)
```

### Response Format

Successful response:

```python
{
    "provider_id": "remitly",
    "success": True,
    "error_message": None,
    "send_amount": 500.0,
    "source_currency": "USD",
    "destination_amount": 28110.0,
    "destination_currency": "PHP",
    "exchange_rate": 56.22,
    "fee": 0.0,
    "payment_method": "bank",
    "delivery_method": "bank",
    "delivery_time_minutes": 1440,
    "timestamp": 1709764388.690806
}
```

Error response:

```python
{
    "provider_id": "remitly",
    "success": False,
    "error_message": "API error: Unable to provide quote for this corridor",
    "send_amount": 500.0,
    "source_currency": "JPY",
    "destination_amount": 0.0,
    "destination_currency": "ZAR",
    "exchange_rate": None,
    "fee": 0.0,
    "payment_method": "bank",
    "delivery_method": "bank",
    "delivery_time_minutes": 1440,
    "timestamp": 1709764388.690806
}
```

## Implementation Details

### API Endpoints

- Base URL: `https://api.remitly.io`
- Quote Endpoint: `/v3/calculator/estimate`

### Authentication

The provider uses a device environment ID and browser fingerprint to authenticate with the Remitly API. It includes appropriate headers and implements retry logic for authentication failures.

### Country and Currency Handling

The provider includes conversion methods between:
- 2-letter and 3-letter country codes
- Country codes and their default currencies
- Currency codes and representative countries

### Error Handling and Retries

The implementation includes sophisticated error handling:
- Automatic retries for network issues
- Session refresh on authentication failures
- Rate limiting detection and backoff
- Proper error categorization via exception types

## Testing

To test the provider, run:

```bash
python -m apps.providers.remitly.test
```

This runs a comprehensive test suite that:
1. Tests quotes for supported corridors (e.g., USD → PHP, USD → INR)
2. Tests error handling for unsupported corridors
3. Verifies the exchange rate method
4. Tests utility methods for country/currency handling

## Error Cases Handled

1. Unsupported corridors
2. Authentication failures
3. Network issues with automatic retries
4. Rate limiting with backoff
5. API errors
6. Invalid responses

## Integration with the Aggregator

This provider follows the aggregator's standardized format for easy integration into the comparison engine. It implements the abstract methods required by the `RemittanceProvider` base class:

- `get_quote()`: Get a standardized quote for a specific corridor
- `get_exchange_rate()`: Legacy method for backward compatibility
- `get_supported_countries()`: List countries in ISO alpha-2 format
- `get_supported_currencies()`: List supported currencies in ISO format

## Requirements

- Python 3.8+
- `requests` library
- `urllib3` library 

## Usage

### Basic Usage

```python
from decimal import Decimal
from apps.providers.factory import ProviderFactory

# Get an instance of the Remitly provider
remitly = ProviderFactory.get_provider('remitly')

# Get exchange rate for USD to MXN transfer
result = remitly.get_exchange_rate(
    send_amount=Decimal("500.00"),
    send_currency="USD",
    receive_country="MX",
    receive_currency="MXN"
)

print(f"Exchange rate: {result['exchange_rate']}")
print(f"Fee: {result['fee']} {result['source_currency']}")
print(f"Recipient will receive: {result['destination_amount']} {result['destination_currency']}")
```

### Using Different Source Countries

```python
from decimal import Decimal
from apps.providers.factory import ProviderFactory

# Get an instance of the Remitly provider
remitly = ProviderFactory.get_provider('remitly')

# Example EUR from Spain to Colombia
eur_result = remitly.get_exchange_rate(
    send_amount=Decimal("400.00"),
    send_currency="EUR",
    receive_country="CO",
    receive_currency="COP"
)

# Example GBP from UK to Nigeria
gbp_result = remitly.get_exchange_rate(
    send_amount=Decimal("600.00"),
    send_currency="GBP",
    receive_country="NG",
    receive_currency="NGN"
)

# Example AUD from Australia to Vietnam
aud_result = remitly.get_exchange_rate(
    send_amount=Decimal("500.00"),
    send_currency="AUD",
    receive_country="VN",
    receive_currency="VND"
)

print(f"EUR to COP: {eur_result['exchange_rate']}, Fee: {eur_result['fee']} EUR")
print(f"GBP to NGN: {gbp_result['exchange_rate']}, Fee: {gbp_result['fee']} GBP")
print(f"AUD to VND: {aud_result['exchange_rate']}, Fee: {aud_result['fee']} AUD")
```

### Retrieving Supported Countries

```python
from apps.providers.factory import ProviderFactory

remitly = ProviderFactory.get_provider('remitly')

# Get list of supported source countries
source_countries = remitly.get_source_countries()
print(f"Number of source countries: {len(source_countries)}")
for country in source_countries[:5]:  # Show first 5
    print(f"{country['country_name']} ({country['country_code']}) - {country['currency_code']}")

# Get list of supported destination countries
dest_countries = remitly.get_supported_countries()
print(f"Number of destination countries: {len(dest_countries)}")
```

### Custom Configuration

```python
from apps.providers.remitly.integration import RemitlyProvider

# Initialize with custom parameters
remitly = RemitlyProvider(
    device_env_id="your-device-env-id",  # Custom device environment ID
    user_agent="YourApp/1.0",  # Custom user agent
    timeout=60  # Custom timeout in seconds
)

# Use provider methods
countries = remitly.get_supported_countries()
payment_methods = remitly.get_payment_methods(target_country="PH")
delivery_methods = remitly.get_delivery_methods(target_country="PH")
```

### Using with Context Manager

```python
from apps.providers.factory import ProviderFactory

with ProviderFactory.get_provider('remitly') as remitly:
    # Get exchange rates for multiple corridors with different source currencies
    corridors = [
        {"source_currency": "USD", "country": "MX", "currency": "MXN"},
        {"source_currency": "EUR", "country": "MA", "currency": "MAD"},
        {"source_currency": "GBP", "country": "IN", "currency": "INR"},
        {"source_currency": "CAD", "country": "PH", "currency": "PHP"},
    ]
    
    for corridor in corridors:
        result = remitly.get_exchange_rate(
            send_amount=Decimal("1000.00"),
            send_currency=corridor["source_currency"],
            receive_country=corridor["country"],
            receive_currency=corridor["currency"]
        )
        
        print(f"{corridor['source_currency']} to {corridor['country']} Rate: {result['exchange_rate']}, Fee: {result['fee']}")
```

## Headers and Authentication

This provider requires specific headers for API requests:

- `Remitly-DeviceEnvironmentID` - A unique identifier used by Remitly for device fingerprinting
- Browser fingerprint data for Branch analytics

The implementation handles these internally and will automatically include the necessary headers when making requests.

## Error Handling

The provider throws custom exceptions for different failure scenarios:

- `RemitlyError` - Base exception for all Remitly-related errors
- `RemitlyAuthenticationError` - Authentication issues
- `RemitlyConnectionError` - Network connection issues
- `RemitlyValidationError` - Input validation errors
- `RemitlyRateLimitError` - Rate limit exceeded

Example of handling errors:

```python
from apps.providers.remitly.exceptions import RemitlyError, RemitlyConnectionError

try:
    result = remitly.get_exchange_rate(
        send_amount=Decimal("500.00"),
        send_currency="USD",
        receive_country="MX"
    )
except RemitlyConnectionError as e:
    print(f"Connection error: {e}")
except RemitlyError as e:
    print(f"Remitly API error: {e}")
```

## Supported Countries

### Source Countries

The provider supports sending money from the following countries:

- United States (USD)
- Canada (CAD)
- United Kingdom (GBP)
- Spain, Germany, France, Italy and other Eurozone countries (EUR)
- Australia (AUD)
- New Zealand (NZD)
- Singapore (SGD)
- Sweden (SEK)
- Norway (NOK)
- Denmark (DKK)

### Destination Countries

The provider supports sending money to 75+ countries across these regions:

- Latin America: Mexico, Colombia, Brazil, Peru, etc.
- Asia: Philippines, India, China, Vietnam, Thailand, etc.
- Africa: Nigeria, Kenya, Ghana, Morocco, etc.
- Europe: Spain, UK, Germany, France, etc.
- Middle East: UAE, Saudi Arabia, etc.
- Oceania: Australia, New Zealand, Fiji

To see the complete list of supported countries:

```python
remitly = ProviderFactory.get_provider('remitly')
countries = remitly.get_supported_countries()
for country in countries:
    print(f"{country['country_name']} ({country['country_code']})")
```

## Running Tests

You can run the included test script to verify the integration:

```bash
python apps/providers/remitly/test.py
```

The test script will:
1. Test exchange rates for multiple corridors with different source currencies
2. Show the list of supported source and destination countries

## Notes

- The device environment ID is stored as a constant in the provider class. In a production environment, you might want to fetch this dynamically or store it in your environment variables or configuration.
- For the Branch browser fingerprint data, the implementation uses a default fingerprint. In a production environment, you might want to generate this dynamically or omit it if not required. 