# RemitScout Quotes System

Core quote storage, caching, and API systems for RemitScout.

## Features

- RESTful API for remittance quotes
- PostgreSQL storage for quote data
- Redis caching with intelligent invalidation
- Signal-based cache updates
- Management commands for cache control

## Architecture

### Database Models

- `Provider`: Stores remittance provider information
- `FeeQuote`: Stores fees and rates for specific corridors
- `QuoteQueryLog`: Logs quote requests for analytics

### Caching System

Cache keys:
- Quote: `v1:fee:{source_country}:{dest_country}:{source_currency}:{dest_currency}:{amount}`
- Corridor: `corridor:{source_country}:{dest_country}`
- Provider: `provider:{provider_id}`
- Corridor rate: `corridor_rate:{source_country}:{dest_country}:{source_currency}:{dest_currency}`

## API Usage

### Get Quotes Endpoint

**Endpoint:** `GET /api/quotes/`

**Parameters:**
- `source_country`: Source country code (e.g., "US")
- `dest_country`: Destination country code (e.g., "MX")
- `source_currency`: Source currency code (e.g., "USD")
- `dest_currency`: Destination currency code (e.g., "MXN")
- `amount`: Decimal amount to send
- `sort_by`: (Optional) Sorting criteria - "best_rate", "lowest_fee", "fastest_time", or "best_value"
- `force_refresh`: (Optional) Boolean to bypass cache and force fresh data

**Example:**

```
GET /api/quotes/?source_country=US&dest_country=MX&source_currency=USD&dest_currency=MXN&amount=1000&sort_by=best_rate
```

**Response:**

```json
{
  "success": true,
  "elapsed_seconds": 0.432,
  "source_country": "US",
  "dest_country": "MX",
  "source_currency": "USD",
  "dest_currency": "MXN",
  "amount": 1000.0,
  "quotes": [
    {
      "provider_id": "Wise",
      "success": true,
      "exchange_rate": 17.94,
      "fee": 8.42,
      "destination_amount": 17855.09,
      "delivery_time_minutes": 1440,
      "payment_method": "Card",
      "delivery_method": "bank_deposit"
    },
    {
      "provider_id": "Xoom",
      "success": true,
      "exchange_rate": 17.78,
      "fee": 0.0,
      "destination_amount": 17780.0,
      "delivery_time_minutes": 2880,
      "payment_method": "Card",
      "delivery_method": "bank_deposit"
    }
  ],
  "cache_hit": true,
  "timestamp": "2023-03-10T12:34:56.789Z",
  "filters_applied": {
    "sort_by": "best_rate",
    "max_delivery_time_minutes": null,
    "max_fee": null
  }
}
```

## Performance Considerations

- The caching system reduces load on external provider APIs by caching results
- The corridor availability caching prevents unnecessary API calls for unsupported corridors
- TTL jitter prevents cache stampedes
- The database schema is designed with appropriate indexes for common query patterns 