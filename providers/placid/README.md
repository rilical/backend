# Placid Provider Implementation

This directory contains the implementation for the Placid remittance provider, following the standardized format required by the RemitScout aggregator.

## Overview

Placid is a remittance provider that supports money transfers to multiple corridors from supported source countries. The integration:

- Fetches exchange rates from Placid's internal API
- Provides quotes for money transfers between supported currencies
- Maps Placid's internal corridor codes to standardized ISO country and currency codes
- Returns properly formatted responses according to the aggregator's requirements

## Supported Corridors

Placid supports the following destination corridors:

| Corridor Code | ISO Country | ISO Currency | Country Name |
|---------------|-------------|--------------|--------------|
| PAK           | PK          | PKR          | Pakistan     |
| IND           | IN          | INR          | India        |
| BGD           | BD          | BDT          | Bangladesh   |
| PHL           | PH          | PHP          | Philippines  |
| NPL           | NP          | NPR          | Nepal        |
| LKA           | LK          | LKR          | Sri Lanka    |
| IDN           | ID          | IDR          | Indonesia    |
| VNM           | VN          | VND          | Vietnam      |

## Supported Source Countries/Currencies

Placid accepts remittances from the following source countries and currencies:

| ISO Country | ISO Currency | Name           |
|-------------|--------------|----------------|
| US          | USD          | United States  |
| GB          | GBP          | United Kingdom |
| CA          | CAD          | Canada         |
| AU          | AUD          | Australia      |
| EU*         | EUR          | Eurozone       |

*Note: EU is used as a placeholder for European countries using EUR.

## Usage Example

```python
from decimal import Decimal
from apps.providers.placid.integration import PlacidProvider

# Initialize provider
provider = PlacidProvider()

# Get a quote for USD -> INR
quote = provider.get_quote(
    amount=Decimal('1000.00'),
    source_currency='USD',
    dest_currency='INR',
    source_country='US',
    dest_country='IN',
    payment_method='bank',
    delivery_method='bank'
)

# Print results
if quote['success']:
    print(f"Exchange rate: {quote['exchange_rate']}")
    print(f"Amount to be received: {quote['destination_amount']} {quote['destination_currency']}")
    print(f"Estimated delivery time: {quote['delivery_time_minutes'] / 60} hours")
else:
    print(f"Error: {quote['error_message']}")
```

## Mapping Files

The `mapping.py` file provides translations between Placid's internal codes and standardized ISO codes:

- `CORRIDOR_TO_ISO`: Maps Placid corridor codes to ISO country/currency codes
- `CURRENCY_TO_CORRIDOR`: Maps ISO currency codes to Placid corridor codes
- `SUPPORTED_SOURCE_COUNTRIES`: Maps source country codes to their currencies

## Error Handling

Placid-specific errors are defined in `exceptions.py` and include:

- `PlacidError`: Base class for all Placid errors
- `PlacidConnectionError`: Network or connection issues
- `PlacidApiError`: General API errors
- `PlacidResponseError`: Response parsing issues
- `PlacidCorridorUnsupportedError`: Unsupported corridor requested

All errors provide details about the specific failure to help with troubleshooting.

## Implementation Notes

- The implementation makes requests to Placid's web interface
- Exchange rates are extracted from the HTML response using regex pattern matching
- No API keys or authentication are required (utilizing public endpoints)
- Default delivery time is set to 24 hours (1440 minutes)
- Default payment and delivery methods are set to "bank" 