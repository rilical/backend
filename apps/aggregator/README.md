# RemitScout Aggregator

The RemitScout Aggregator is a powerful tool that aggregates quotes from multiple remittance providers to help users find the best rates, lowest fees, or fastest delivery times for international money transfers.

## Features

- **Simple API**: Only requires minimal parameters (source/dest country, currency, amount)
- **Concurrent Processing**: Runs all provider requests in parallel for fast response times
- **Multiple Sorting Options**: Sort by best exchange rate, lowest fee, or fastest delivery time
- **Flexible Filtering**: Exclude specific providers or set maximum limits for fees/delivery times
- **Comprehensive Results**: Returns detailed information about each provider's quote
- **Robust Error Handling**: Captures and reports provider-specific errors
- **Provider Configuration**: Enable/disable providers through the configuration interface

## Supported Providers

The aggregator currently integrates with the following providers:

| Provider | Description | Status |
|----------|-------------|--------|
| XE | Global currency and foreign exchange service | ✅ Working |
| Remitly | Digital remittance service focused on immigrant communities | ✅ Working |
| RIA | Global money transfer company | ✅ Working |
| Wise (TransferWise) | Online money transfer service | ✅ Working |
| TransferGo | Digital remittance service for migrants | ❌ Limited corridors |
| Xoom (PayPal) | PayPal's international money transfer service | ✅ Working |
| SingX | Singapore-based money transfer service | ❌ Limited source countries |
| Paysend | Global card-to-card money transfer platform | ✅ Working |
| Western Union | Global financial services and communications company | ❌ Import issues |
| AlAnsari | UAE-based exchange and transfer service | ⚠️ Testing |
| Remitbee | Canada-based digital remittance service | ⚠️ Testing |
| InstaRem | Singapore-based cross-border payment company | ⚠️ Testing |
| Pangea | US-based mobile money transfer service | ⚠️ Testing |
| KoronaPay | Russia-based money transfer service | ⚠️ Testing |
| Mukuru | Africa-focused remittance provider | ⚠️ Testing |
| Rewire | European digital banking service for migrants | ⚠️ Testing |
| Sendwave | Mobile money transfer app focused on Africa | ⚠️ Testing |
| WireBarley | South Korea-based global remittance service | ⚠️ Testing |
| OrbitRemit | New Zealand-based money transfer service | ⚠️ Testing |
| Dahabshiil | African money transfer operator | ⚠️ Testing |

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
for provider_id, quote in result.get("quotes", {}).items():
    print(f"{provider_id}: Rate {quote['exchange_rate']}, Fee {quote['fee']}, Recipient gets {quote['destination_amount']} {quote['destination_currency']}")
```

### Sorting Results

```python
# Sort by best exchange rate (default)
result = Aggregator.get_all_quotes(
    source_country="US",
    dest_country="IN",
    source_currency="USD",
    dest_currency="INR",
    amount=Decimal("1000.00"),
    sort_by="best_rate"
)

# Sort by lowest fee
result = Aggregator.get_all_quotes(
    source_country="US",
    dest_country="IN",
    source_currency="USD",
    dest_currency="INR",
    amount=Decimal("1000.00"),
    sort_by="lowest_fee"
)

# Sort by fastest delivery time
result = Aggregator.get_all_quotes(
    source_country="US",
    dest_country="IN",
    source_currency="USD",
    dest_currency="INR",
    amount=Decimal("1000.00"),
    sort_by="fastest_time"
)
```

### Filtering Results

```python
# Exclude specific providers
result = Aggregator.get_all_quotes(
    source_country="US",
    dest_country="IN",
    source_currency="USD",
    dest_currency="INR",
    amount=Decimal("1000.00"),
    exclude_providers=["XoomProvider"]
)

# Set maximum delivery time (in minutes)
result = Aggregator.get_all_quotes(
    source_country="US",
    dest_country="IN",
    source_currency="USD",
    dest_currency="INR",
    amount=Decimal("1000.00"),
    max_delivery_time_minutes=2880  # 48 hours
)

# Set maximum fee
result = Aggregator.get_all_quotes(
    source_country="US",
    dest_country="IN",
    source_currency="USD",
    dest_currency="INR",
    amount=Decimal("1000.00"),
    max_fee=10.0
)
```

### Advanced Custom Filtering

```python
# Define a custom filter function
def custom_filter(quote):
    # Only include quotes with exchange rate above 85
    if quote.get("exchange_rate", 0) < 85:
        return False
    
    # Only include quotes with fee below $10
    if quote.get("fee", 0) > 10:
        return False
    
    return True

# Apply custom filter function
result = Aggregator.get_all_quotes(
    source_country="US",
    dest_country="IN",
    source_currency="USD",
    dest_currency="INR",
    amount=Decimal("1000.00"),
    filter_fn=custom_filter
)
```

### Using the Configurator

The aggregator comes with a configuration utility that allows you to enable/disable providers and set other configuration options:

```python
from apps.aggregator.configurator import AggregatorConfig

# Initialize the configurator
config = AggregatorConfig()

# Disable providers you don't want to use
config.disable_provider("SingXProvider")
config.disable_provider("TransferGoProvider")

# Set default sorting method
config.set_default_sort("lowest_fee")  # Options: best_rate, lowest_fee, fastest_time, best_value

# Get parameters to use with the aggregator
params = config.get_aggregator_params()

# Use the parameters with the aggregator
from apps.aggregator.aggregator import Aggregator
from decimal import Decimal

result = Aggregator.get_all_quotes(
    source_country="US",
    dest_country="IN",
    source_currency="USD",
    dest_currency="INR",
    amount=Decimal("1000.00"),
    **params  # This includes the exclude_providers, sort_by, and max_workers settings
)
```

You can also use the configurator from the command line:

```bash
python -m apps.aggregator.configurator
```

This will show the current configuration status and list of enabled/disabled providers.

## Response Format

The aggregator returns a standardized format:

```json
{
  "success": true,
  "elapsed_seconds": 5.23,
  "source_country": "US",
  "dest_country": "IN",
  "source_currency": "USD",
  "dest_currency": "INR",
  "amount": 1000.0,
  "all_providers": [
    {
      "provider_id": "XE",
      "success": true,
      "error_message": null,
      "exchange_rate": 86.64,
      "fee": 0.0,
      "source_amount": 1000.0,
      "source_currency": "USD",
      "destination_amount": 86636.98,
      "destination_currency": "INR",
      "delivery_time_minutes": 4320,
      "payment_method": "bank account",
      "delivery_method": "bank deposit",
      "timestamp": "2023-08-06T12:34:56Z"
    },
    {
      "provider_id": "Wise",
      "success": true,
      "error_message": null,
      "exchange_rate": 87.19,
      "fee": 7.33,
      "source_amount": 1000.0,
      "source_currency": "USD",
      "destination_amount": 86550.9,
      "destination_currency": "INR",
      "delivery_time_minutes": 1440,
      "payment_method": "bank account",
      "delivery_method": "bank deposit",
      "timestamp": "2023-08-06T12:34:56Z"
    }
  ],
  "quotes": [
    {
      "provider_id": "Wise",
      "success": true,
      "error_message": null,
      "exchange_rate": 87.19,
      "fee": 7.33,
      "source_amount": 1000.0,
      "source_currency": "USD",
      "destination_amount": 86550.9,
      "destination_currency": "INR",
      "delivery_time_minutes": 1440,
      "payment_method": "bank account",
      "delivery_method": "bank deposit",
      "timestamp": "2023-08-06T12:34:56Z"
    },
    {
      "provider_id": "XE",
      "success": true,
      "error_message": null,
      "exchange_rate": 86.64,
      "fee": 0.0,
      "source_amount": 1000.0,
      "source_currency": "USD",
      "destination_amount": 86636.98,
      "destination_currency": "INR",
      "delivery_time_minutes": 4320,
      "payment_method": "bank account",
      "delivery_method": "bank deposit",
      "timestamp": "2023-08-06T12:34:56Z"
    }
  ],
  "filters_applied": {
    "sort_by": "best_rate",
    "max_delivery_time_minutes": null,
    "max_fee": null,
    "custom_filter": false
  }
}
```

## Error Handling

When a provider fails to provide a quote, the error is captured and returned in the response:

```json
{
  "success": true,
  "elapsed_seconds": 6.12,
  "source_country": "US",
  "dest_country": "IN",
  "source_currency": "USD",
  "dest_currency": "INR",
  "amount": 1000.0,
  "all_providers": [
    {
      "provider_id": "SingX",
      "success": false,
      "error_message": "Unsupported source country: US",
      "timestamp": "2023-08-06T12:34:56Z"
    }
  ],
  "quotes": [],
  "errors": {
    "SingX": {
      "provider_id": "SingX",
      "error_message": "Unsupported source country: US"
    }
  },
  "filters_applied": {
    "sort_by": "best_rate",
    "max_delivery_time_minutes": null,
    "max_fee": null,
    "custom_filter": false
  }
}
```

## Extending the Aggregator

To add a new provider to the aggregator:

1. Implement a provider class that extends `RemittanceProvider` base class
2. Implement the `get_quote` method with the standard parameters
3. Add the provider instance to the `PROVIDERS` list in the Aggregator class
4. Add any necessary parameter mappings to the `PROVIDER_PARAMS` dictionary

## Performance Considerations

- The aggregator uses concurrent execution to call all providers simultaneously
- Default timeout for provider requests is 30 seconds
- To limit concurrency, use the `max_workers` parameter when calling `get_all_quotes` 