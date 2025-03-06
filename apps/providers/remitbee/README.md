# Remitbee Integration

This package implements integration with Remitbee, a digital money transfer service that offers competitive exchange rates for international remittances.

## Overview

The integration accesses Remitbee's public quote API to fetch exchange rates and fees for international money transfers. It primarily focuses on transfers from Canada (CAD) to various international destinations.

Key features:
- Extract country and currency information from Remitbee's website
- Retrieve real-time exchange rates and fees for money transfers
- Support for special rates when available

## API Endpoints

The integration uses these Remitbee endpoints:

- **Calculate Money Transfer**: `POST https://api.remitbee.com/public-services/calculate-money-transfer`
  - Provides quotes for specific money transfer corridors
  - Returns exchange rates, fees, and estimated delivery time

## Setup and Usage

### Requirements

- Python 3.7+
- `requests`
- `beautifulsoup4` (for HTML parsing)

### Getting Country Data

The integration requires country data from Remitbee to map country codes to the internal IDs used by their API.

You can provide this data in two ways:

1. **HTML file**: Create a file with the HTML from Remitbee's country dropdown (each `<li>` with a `data-item` attribute).

2. **Cached JSON**: The integration will save parsed country data to a JSON file for future use.

### Basic Usage

```python
from decimal import Decimal
from apps.providers.remitbee.integration import RemitbeeProvider

# Initialize the provider (with optional HTML file for country data)
provider = RemitbeeProvider(countries_html_file="remitbee_countries.html")

# Get exchange rate for sending 1000 CAD to India
result = provider.get_exchange_rate(
    send_amount=Decimal("1000.00"),
    send_currency="CAD",
    receive_country="IN"
)

# Print the result
print(f"Exchange Rate: {result.get('exchange_rate')}")
print(f"Fee: {result.get('fee')} CAD")
print(f"Recipient Gets: {result.get('receive_amount')} {result.get('receive_currency')}")
```

## Testing

A test script is provided in `test_remitbee.py`. You can run it to test the integration:

```bash
# Run with cached country data
python apps/providers/remitbee/test_remitbee.py

# Run with a specific HTML file
python apps/providers/remitbee/test_remitbee.py path/to/remitbee_countries.html
```

## Notes

- Remitbee primarily supports sending money from Canada (CAD)
- The API might have rate limits or require additional authentication for production use
- For full integration, you would need to implement the complete remittance flow, including user authentication, payment processing, and transaction tracking 