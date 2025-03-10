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

RemitScout is a powerful remittance comparison platform that helps users find the best deals when sending money internationally. This repository contains the backend services that power the RemitScout platform.

## Architecture Overview

RemitScout follows a modular architecture with the following main components:

- **Provider Integrations**: Standardized interfaces to remittance service providers (e.g., Wise, Xoom, XE)
- **Aggregator**: Core service that collects and compares quotes from multiple providers
- **API Layer**: REST API for accessing remittance comparison features
- **Utils**: Shared utility functions and models

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
├── examples.py    # Usage examples
├── workflow.py    # Sample workflow
├── cli.py         # Command-line interface
└── README.md      # Aggregator-specific documentation
```

### Aggregator Features

- **Parallel Processing**: Calls all providers concurrently for fast response times
- **Multiple Sorting Options**: Sort by best rate, lowest fee, or fastest delivery time
- **Flexible Filtering**: Filter results based on various criteria
- **Robust Error Handling**: Captures and reports provider-specific errors
- **Comprehensive Results**: Returns detailed information from each provider

## Supported Providers

The platform now integrates with 20+ remittance providers, offering comprehensive coverage for global money transfers:

| Provider | Status | Description |
|----------|--------|-------------|
| Wise (TransferWise) | ✅ Working | Online money transfer service |
| XE | ✅ Working | Global currency and foreign exchange service |
| Remitly | ✅ Working | Digital remittance service |
| RIA | ✅ Working | Global money transfer company |
| Xoom (PayPal) | ✅ Working | PayPal's international money transfer service |
| Paysend | ✅ Working | Global card-to-card money transfer platform |
| AlAnsari | ⚠️ Testing | UAE-based exchange and transfer service |
| Remitbee | ⚠️ Testing | Canada-based digital remittance service |
| InstaRem | ⚠️ Testing | Singapore-based cross-border payment company |
| Pangea | ⚠️ Testing | US-based mobile money transfer service |
| KoronaPay | ⚠️ Testing | Russia-based money transfer service |
| Mukuru | ⚠️ Testing | Africa-focused remittance provider |
| Rewire | ⚠️ Testing | European digital banking service for migrants |
| Sendwave | ⚠️ Testing | Mobile money transfer app focused on Africa |
| WireBarley | ⚠️ Testing | South Korea-based global remittance service |
| OrbitRemit | ⚠️ Testing | New Zealand-based money transfer service |
| Dahabshiil | ⚠️ Testing | African money transfer operator |
| SingX | ⚠️ Limited | Singapore-based money transfer service |
| TransferGo | ⚠️ Limited | Digital remittance service for migrants |
| Western Union | ❌ Pending | Global financial services company |

Refer to the [Provider Support Matrix](apps/providers/README.md) for detailed information about corridor coverage and API capabilities for each provider.

## Getting Started

### Prerequisites

- Python 3.8+
- pip

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/remitscout-backend.git
cd remitscout-backend
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables (create a `.env` file):
```
# Provider API keys
WISE_API_KEY=your_wise_api_key
XE_API_KEY=your_xe_api_key
REMITLY_API_KEY=your_remitly_api_key
# ... add other provider keys as needed

# Other configuration
LOG_LEVEL=INFO
```

### Running the Examples

To run the basic examples:
```bash
PYTHONPATH=/path/to/remitscout-backend python3 apps/aggregator/examples.py
```

To run the workflow example:
```bash
PYTHONPATH=/path/to/remitscout-backend python3 apps/aggregator/workflow.py
```

### Using the CLI

The CLI provides a convenient way to compare remittances:
```bash
PYTHONPATH=/path/to/remitscout-backend python3 apps/aggregator/cli.py \
  --source-country US \
  --dest-country IN \
  --source-currency USD \
  --dest-currency INR \
  --amount 1000 \
  --sort-by best_rate \
  --max-fee 10
```

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
for quote in result.get("quotes", []):
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

### Configuration and Provider Management

The aggregator includes a configuration utility that allows you to enable/disable providers and customize the behavior:

```python
from apps.aggregator.configurator import AggregatorConfig

# Print current status of all providers
config = AggregatorConfig()
config.print_status()

# Disable a provider that you don't want to use
config.disable_provider("TransferGoProvider")

# Set default sort order
config.set_default_sort("lowest_fee")

# Get configured parameters to use with the aggregator
params = config.get_aggregator_params()
result = Aggregator.get_all_quotes(
    source_country="US",
    dest_country="IN",
    source_currency="USD",
    dest_currency="INR",
    amount=Decimal("1000.00"),
    **params  # Applies all your configuration settings
)
```

### Corridor Support Analysis

You can analyze which providers support which corridors using the corridor support analysis tool:

```bash
PYTHONPATH=/path/to/remitscout-backend python3 apps/aggregator/tests/test_corridor_support.py
```

This will test all providers with common corridors and generate a detailed report of provider support.

## Project Structure

```
backend/
├── apps/
│   ├── aggregator/  # Aggregator module
│   ├── api/         # API endpoints
│   └── providers/   # Provider integrations
│       ├── wise/
│       ├── xe/
│       ├── remitly/
│       └── ...
├── utils/           # Shared utilities
│   ├── currency/
│   ├── country/
│   └── ...
├── tests/           # Test suite
├── requirements.txt # Dependencies
└── README.md        # This file
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit your changes: `git commit -am 'Add new feature'`
4. Push to the branch: `git push origin feature-name`
5. Submit a pull request

## Adding a New Provider

To add a new remittance provider:

1. Create a new directory under `apps/providers/`
2. Implement the provider interface (see existing providers for examples)
3. Add the provider to the aggregator's provider list
4. Update parameter mappings if needed
5. Test the provider with the aggregator

## License

This project is licensed under the MIT License - see the LICENSE file for details. 