# Sendwave Provider Integration

This module implements integration with Sendwave's public API to fetch exchange rates, fees, and other pricing information for remittances.

## Features

- Fetches real-time quotes from Sendwave's pricing API
- Supports multiple corridors (USD to Philippines, Kenya, Uganda, Ghana)
- Handles different delivery methods (e.g., GCash for Philippines, M-Pesa for Kenya)
- Provides detailed responses with exchange rates, fees, and any applicable promotions
- Includes proper exception handling for various error scenarios

## Usage

Basic usage example:

```python
from apps.providers.sendwave import WaveProvider
from decimal import Decimal

# Initialize the provider
wave = WaveProvider()

# Get a quote
try:
    quote = wave.get_exchange_rate(
        send_amount=Decimal("500"),
        send_currency="USD",
        receive_country="PH"  # Philippines
    )

    # Check if successful
    if quote["success"]:
        print(f"Exchange rate: {quote['exchange_rate']}")
        print(f"Fees: {quote['fee']}")
        print(f"Receive amount: {quote['receive_amount']} {quote['receive_currency']}")
        if quote.get("promotions"):
            print("Promotions:")
            for promo in quote["promotions"]:
                print(f"  - {promo['description']}: {promo['value']} {quote['send_currency']}")
    else:
        print(f"Error: {quote['error_message']}")
except Exception as e:
    print(f"Error: {e}")
```

## Advanced Options

You can specify additional parameters for certain corridors:

```python
# For Philippines with GCash as the delivery method
quote = wave.get_exchange_rate(
    send_amount=Decimal("500"),
    send_currency="USD",
    receive_country="PH",
    segment_name="ph_gcash",
    send_country_iso2="us"
)

# For Kenya with M-Pesa as the delivery method
quote = wave.get_exchange_rate(
    send_amount=Decimal("1000"),
    send_currency="USD",
    receive_country="KE",
    segment_name="ke_mpesa",
    send_country_iso2="us"
)
```

## Exception Handling

This module provides several custom exceptions for better error handling:

```python
from apps.providers.sendwave.exceptions import (
    SendwaveError,               # Base exception for all Sendwave errors
    SendwaveConnectionError,     # Connection issues with the API
    SendwaveApiError,            # API returns an error response
    SendwaveResponseError,       # Invalid or unexpected response format
    SendwaveCorridorUnsupportedError  # Unsupported corridor
)

try:
    quote = wave.get_exchange_rate(...)
except SendwaveCorridorUnsupportedError as e:
    print(f"Corridor not supported: {e}")
except SendwaveConnectionError as e:
    print(f"Connection error: {e}")
except SendwaveApiError as e:
    print(f"API error: {e}")
except SendwaveError as e:
    print(f"General error: {e}")
```

## Testing

This module includes a CLI test tool at `test_wave_cli.py` that can be used to verify the integration:

```bash
# Ensure you're in the project root directory
cd /path/to/backend

# Run the test script
PYTHONPATH=. python3 -m apps.providers.sendwave.test_wave_cli --amount 500 --currency USD --country PH
```

You can also specify additional parameters:

```bash
PYTHONPATH=. python3 -m apps.providers.sendwave.test_wave_cli --amount 1000 --currency USD --country KE --segment ke_mpesa
```

## Supported Corridors

Currently supported corridors include:

- USD → PHP (Philippines)
- USD → KES (Kenya)

Additional corridors can be added by updating the `SUPPORTED_CORRIDORS` list in the `WaveProvider` class. 