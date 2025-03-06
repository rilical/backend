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