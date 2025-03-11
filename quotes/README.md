# RemitScout Quotes System

This module implements the quote storage, caching, and API systems for RemitScout.

## Features

- RESTful API for retrieving remittance quotes
- PostgreSQL database storage for quote data
- Redis caching system with intelligent invalidation
- Signal-based cache updates
- Management commands for cache control

## Architecture

### Database Models

- `Provider`: Stores information about remittance providers
- `FeeQuote`: Stores fee and rate information for specific corridors
- `QuoteQueryLog`: Logs all quote requests for analytics

### Caching System

The caching system uses Redis for high-performance in-memory storage with the following features:

#### Cache Key Design

Cache keys follow a structured pattern:

- Quote caches: `v1:fee:{source_country}:{dest_country}:{source_currency}:{dest_currency}:{amount}`
- Corridor caches: `corridor:{source_country}:{dest_country}`
- Provider caches: `provider:{provider_id}`

The `v1:` prefix allows for version upgrades without breaking existing cached data.

#### TTL and Jitter

- Different TTLs are set for different types of data:
  - Quotes: 30 minutes
  - Provider data: 24 hours
  - Corridor info: 12 hours
- Each TTL has jitter (randomization) to prevent the "thundering herd" problem

#### Invalidation Strategies

1. **Automatic invalidation** via signals:
   - When a `FeeQuote` is saved or deleted, related cache entries are automatically invalidated
   - When a `Provider` is updated, related cache entries are invalidated

2. **Manual invalidation** via management commands:
   - `python manage.py cache_utils --action invalidate_all` - Invalidate all quote caches
   - `python manage.py cache_utils --action invalidate_corridor --source_country US --dest_country MX` - Invalidate specific corridor
   - `python manage.py cache_utils --action invalidate_provider --provider_id XoomProvider` - Invalidate specific provider

3. **Preloading** for performance:
   - `python manage.py cache_utils --action preload_corridors` - Preload corridor availability information

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