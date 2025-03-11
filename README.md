# WorldRemit ScrapeOps Integration

This package provides integration with the WorldRemit service using the ScrapeOps Proxy API to bypass PerimeterX protection.

## Features

- Retrieves exchange rates from WorldRemit
- Gets supported countries and currencies
- Determines available payment methods
- Bypasses PerimeterX protection using ScrapeOps Proxy API

## Installation

1. Install the required dependencies:

```bash
pip install -r requirements.txt
```

2. Ensure you have a valid ScrapeOps API key.

## Usage

### Basic Usage

```python
from apps.providers.worldremit.integration_scrapeops import WorldRemitScrapeOpsProvider
from decimal import Decimal

# Initialize the provider
provider = WorldRemitScrapeOpsProvider(
    api_key="your_scrapeops_api_key",
    render_js=True,  # Enable JavaScript rendering
    use_residential_proxies=True  # Use residential proxies for better success rate
)

# Get exchange rate
exchange_rate = provider.get_exchange_rate(
    send_amount=Decimal("100.00"),
    send_currency="USD",
    receive_country="TR",
    receive_currency=None  # Optional, will use the default currency for the country if not specified
)

# Get supported countries
countries = provider.get_supported_countries()

# Get payment methods
payment_methods = provider.get_payment_methods(
    source_country="US",
    target_country="TR"
)
```

### Testing

A test script is provided to verify the integration:

```bash
./test_worldremit_scrapeops.py --api-key="your_scrapeops_api_key" --test=all
```

Options:
- `--api-key`: Your ScrapeOps API key
- `--render-js`: Enable JavaScript rendering (default: True)
- `--residential`: Use residential proxies (default: True)
- `--country`: Proxy country code (optional)
- `--amount`: Send amount (default: 100.00)
- `--send-currency`: Send currency (default: USD)
- `--send-country`: Send country (default: US)
- `--receive-country`: Receive country (default: TR)
- `--receive-currency`: Receive currency (optional)
- `--timeout`: Request timeout in seconds (default: 60)
- `--test`: Test to run (choices: exchange, countries, payments, all; default: all)

## Security

- Store your ScrapeOps API key securely, preferably in environment variables
- Use a `.env` file for local development (not in version control)
- Use secure environment variables in production

## Troubleshooting

If you encounter issues:

1. Ensure your ScrapeOps API key is valid and has sufficient credits
2. Try increasing the timeout value
3. Enable JavaScript rendering and residential proxies for better success rate
4. Verify that ScrapeOps services are operational 

# RemitScout Backend

**Version: 1.0**

RemitScout is a powerful remittance comparison platform that helps users find the best deals when sending money internationally. This repository contains the backend services that power the RemitScout platform.

## Architecture Overview

RemitScout follows a modular architecture with the following main components:

- **Provider Integrations**: Standardized interfaces to remittance service providers (e.g., Wise, Xoom, XE)
- **Aggregator**: Core service that collects and compares quotes from multiple providers
- **Quotes API**: REST API for accessing remittance comparison features
- **Caching System**: Multi-level Redis-based caching for performance optimization

## Provider Integrations

Each remittance provider is integrated through a standardized interface:

```
apps/providers/
├── provider_name/
│   ├── __init__.py
│   ├── integration.py
│   ├── exceptions.py
│   └── aggregator.py (optional)
```

All providers implement common methods:
- `get_quote()`: Retrieve a quote for sending money
- `get_exchange_rate()`: Get the current exchange rate
- `standardize_response()`: Convert provider-specific formats to our standard format

## Aggregator

The aggregator is the core of the RemitScout system, responsible for:

1. Calling multiple provider integrations concurrently
2. Collecting and standardizing responses
3. Applying filters and sorting results
4. Handling errors gracefully
5. Providing a consolidated response

```
apps/aggregator/
├── __init__.py
├── aggregator.py  # Main aggregator implementation
├── filters.py     # Filtering utilities
└── exceptions.py  # Error handling
```

### Aggregator Features

- **Parallel Processing**: Calls all providers concurrently for fast response times
- **Multiple Sorting Options**: Sort by best rate, lowest fee, or fastest delivery time
- **Flexible Filtering**: Filter results based on various criteria
- **Robust Error Handling**: Captures and reports provider-specific errors

## Caching System

RemitScout uses a sophisticated multi-level caching system:

```
quotes/
├── key_generators.py  # Cache key generation functions
├── cache_utils.py     # Cache utility functions
├── signals.py         # Cache invalidation signals
└── tasks.py           # Scheduled cache maintenance tasks
```

### Caching Features

- **Multi-level Caching**: Different caching strategies for different data types
- **Automatic Invalidation**: Cache entries are automatically invalidated when data changes
- **TTL Management**: Time-to-live settings with jitter to prevent cache stampedes
- **Preloading**: Popular corridors and amounts are proactively cached

See `docs/caching_implementation.md` for detailed documentation on the caching system.

## Supported Providers

The platform integrates with 20+ remittance providers, offering comprehensive coverage for global money transfers:

| Provider | Status | Description |
|----------|--------|-------------|
| Wise (TransferWise) | ✅ Working | Online money transfer service |
| XE | ✅ Working | Global currency and foreign exchange service |
| Remitly | ✅ Working | Digital remittance service |
| RIA | ✅ Working | Global money transfer company |
| Xoom (PayPal) | ✅ Working | PayPal's international money transfer service |
| Paysend | ✅ Working | Global card-to-card money transfer platform |
| Western Union | ✅ Working | Global financial services company |
| TransferGo | ✅ Working | Digital remittance service for migrants |
| SingX | ✅ Working | Singapore-based money transfer service |
| Remitbee | ✅ Working | Canada-based digital remittance service |
| InstaRem | ✅ Working | Singapore-based cross-border payment company |
| Pangea | ✅ Working | US-based mobile money transfer service |
| KoronaPay | ✅ Working | Russia-based money transfer service |
| Mukuru | ✅ Working | Africa-focused remittance provider |
| Rewire | ✅ Working | European digital banking service for migrants |
| Sendwave | ✅ Working | Mobile money transfer app focused on Africa |
| WireBarley | ✅ Working | South Korea-based global remittance service |
| OrbitRemit | ✅ Working | New Zealand-based money transfer service |
| Dahabshiil | ✅ Working | African money transfer operator |
| Intermex | ✅ Working | Latin America-focused remittance provider |
| Placid | ✅ Working | European remittance service |
| RemitGuru | ✅ Working | India-focused remittance service |
| AlAnsari | ✅ Working | UAE-based exchange and transfer service |

## Getting Started

### Prerequisites

- Python 3.8+
- PostgreSQL 12+
- Redis 6+
- pip

### Installation

1. Clone the repository:
```bash
git clone https://github.com/remitscout/backend.git
cd backend
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables (create a `.env` file based on `.env.example`):
```
# Database configuration
DATABASE_URL=postgresql://user:password@localhost:5432/remitscout

# Redis configuration
REDIS_URL=redis://localhost:6379/0

# Cache settings
QUOTE_CACHE_TTL=1800
CORRIDOR_CACHE_TTL=43200

# Provider API keys
WISE_API_KEY=your_wise_api_key
XE_API_KEY=your_xe_api_key
# ... add other provider keys as needed
```

4. Run migrations:
```bash
python manage.py migrate
```

5. Start the development server:
```bash
python manage.py runserver
```

## API Documentation

See `API_DOCUMENTATION.md` for detailed API documentation.

## Usage Examples

### Basic Usage

```python
from decimal import Decimal
from apps.aggregator.aggregator import Aggregator

# Get quotes from all providers
result = Aggregator.get_all_quotes(
    source_country="US",
    dest_country="IN",
    source_currency="USD",
    dest_currency="INR",
    amount=Decimal("1000.00")
)

# Display the results
for quote in result.get("results", []):
    if quote.get("success", False):
        print(f"{quote.get('provider_id')}: rate={quote.get('exchange_rate')}, "
              f"fee={quote.get('fee')}, delivery={quote.get('delivery_time_minutes')} min")
```

### Filtering with Custom Criteria

```python
from apps.aggregator.filters import create_custom_filter

custom_filter = create_custom_filter(
    min_rate=85.0,
    max_fee=10.0,
    max_delivery_time=2880,  # 48 hours
    exclude_providers=["SingXProvider"]
)

result = Aggregator.get_all_quotes(
    source_country="US",
    dest_country="IN",
    source_currency="USD",
    dest_currency="INR",
    amount=Decimal("1000.00"),
    filter_fn=custom_filter,
    sort_by="fastest_time"
)
```

## Project Structure

```
backend/
├── apps/                 # Application modules
│   ├── aggregator/       # Aggregator module
│   ├── providers/        # Provider integrations
│   └── users/            # User management
├── docs/                 # Documentation
│   └── caching_implementation.md
├── quotes/               # Quotes handling and API
│   ├── key_generators.py
│   ├── cache_utils.py
│   ├── signals.py
│   ├── tasks.py
│   └── views.py
├── remit_scout/          # Project settings
│   ├── settings.py
│   └── urls.py
├── tests/                # Test suite
├── API_DOCUMENTATION.md  # API documentation
├── manage.py             # Django management script
├── requirements.txt      # Dependencies
└── README.md             # This file
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Version History

### Version 1.0 (March, 2024)
- Initial production release
- Support for 20+ remittance providers
- Multi-level caching system with automatic invalidation
- RESTful API for quote retrieval
- Flexible filtering and sorting options 