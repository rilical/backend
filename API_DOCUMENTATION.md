# RemitScout API Documentation

**Version: 1.0**

This document provides comprehensive documentation for the RemitScout API, which allows clients to compare remittance services across multiple providers.

## Base URL

- **Development**: `http://localhost:8000/`
- **Production**: Base URL will be provided when deployed to production

## Authentication

API endpoints use the following authentication mechanisms:

- **Public Endpoints**: No authentication required (quotes)
- **Protected Endpoints**: API key required in HTTP header `X-API-Key`

To obtain an API key, contact the RemitScout team.

## Endpoints

### Get Remittance Quotes

`GET /api/quotes/`

Retrieves and compares quotes from multiple remittance providers for a specified money transfer corridor.

#### Query Parameters

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `source_country` | Yes | ISO-3166-1 alpha-2 country code for sending country | "US" |
| `dest_country` | Yes | ISO-3166-1 alpha-2 country code for receiving country | "MX" |
| `source_currency` | Yes | ISO-4217 currency code for sending currency | "USD" |
| `dest_currency` | Yes | ISO-4217 currency code for receiving currency | "MXN" |
| `amount` | Yes | Decimal amount to send | "1000.00" |
| `sort_by` | No | Sorting criteria: "best_rate", "lowest_fee", "fastest_time", "best_value" | "best_rate" |
| `max_delivery_time_minutes` | No | Maximum acceptable delivery time in minutes | 1440 |
| `max_fee` | No | Maximum acceptable fee | 10.00 |
| `force_refresh` | No | Boolean to bypass cache and force fresh quotes | false |

#### Example Request

```
GET /api/quotes/?source_country=US&dest_country=MX&source_currency=USD&dest_currency=MXN&amount=1000&sort_by=best_rate
```

#### Example Response

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
      "provider_id": "wise",
      "provider_name": "Wise (TransferWise)",
      "success": true,
      "exchange_rate": 17.94,
      "fee": 8.42,
      "destination_amount": 17855.09,
      "delivery_time_minutes": 1440,
      "payment_method": "Card",
      "delivery_method": "bank_deposit"
    },
    {
      "provider_id": "xoom",
      "provider_name": "Xoom (PayPal)",
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

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether the request was successful |
| `elapsed_seconds` | number | Time taken to process the request |
| `source_country` | string | Source country code |
| `dest_country` | string | Destination country code |
| `source_currency` | string | Source currency code |
| `dest_currency` | string | Destination currency code |
| `amount` | number | Send amount |
| `quotes` | array | List of quotes from various providers |
| `cache_hit` | boolean | Whether the result was served from cache |
| `timestamp` | string | ISO timestamp when the data was retrieved |
| `filters_applied` | object | Filters that were applied to the results |

### List Available Providers

`GET /api/providers/providers/list/`

Returns a list of all supported remittance providers in the system with their IDs, display names, and logo URLs (if available).

#### Example Request

```
GET /api/providers/providers/list/
```

#### Example Response

```json
{
  "providers": [
    {
      "id": "XE",
      "name": "XE Money Transfer",
      "logo_url": "https://remitscout.com/logos/XE.png"
    },
    {
      "id": "WISE",
      "name": "Wise",
      "logo_url": "https://remitscout.com/logos/WISE.png"
    },
    {
      "id": "REMITLY",
      "name": "Remitly",
      "logo_url": "https://remitscout.com/logos/REMITLY.png"
    },
    {
      "id": "WESTERNUNION",
      "name": "Western Union",
      "logo_url": "https://remitscout.com/logos/WESTERNUNION.png"
    }
  ],
  "count": 4
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `providers` | array | List of provider objects |
| `providers[].id` | string | Unique identifier for the provider (used in API calls) |
| `providers[].name` | string | Human-readable display name of the provider |
| `providers[].logo_url` | string | URL to the provider's logo image (if available) |
| `count` | integer | Total number of providers returned |

### Get Provider Details

`GET /api/providers/providers/{provider_id}/details/`

Returns basic information about a specific remittance provider, including supported payment and delivery methods.

#### Path Parameters

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `provider_id` | Yes | The unique identifier of the provider | "XE" |

#### Example Request

```
GET /api/providers/providers/XE/details/
```

#### Example Response

```json
{
  "id": "XE",
  "name": "XE Money Transfer",
  "logo_url": "https://remitscout.com/logos/XE.png",
  "website": "https://www.xe.com/send-money/",
  "transfer_types": ["international"],
  "supported_payment_methods": ["bank_transfer", "debit_card", "credit_card"],
  "supported_delivery_methods": ["bank_deposit"]
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier for the provider |
| `name` | string | Human-readable display name of the provider |
| `logo_url` | string | URL to the provider's logo image |
| `website` | string | URL to the provider's website |
| `transfer_types` | array | Types of transfers supported (e.g., "international", "domestic") |
| `supported_payment_methods` | array | List of supported payment methods |
| `supported_delivery_methods` | array | List of supported delivery methods |

## Error Handling

The API uses standard HTTP status codes and returns error details in a consistent format:

```json
{
  "success": false,
  "error": {
    "code": "INVALID_PARAMETERS",
    "message": "Required parameter 'amount' is missing",
    "details": {
      "missing_params": ["amount"]
    }
  }
}
```

Common error codes:
- `INVALID_PARAMETERS`: Missing or invalid request parameters
- `PROVIDER_ERROR`: Error occurred with one or more providers
- `UNSUPPORTED_CORRIDOR`: The requested corridor is not supported
- `RATE_LIMIT_EXCEEDED`: Too many requests from this client

## Rate Limiting

API requests are rate-limited to ensure fair usage:
- Public endpoints: 60 requests per minute
- Authenticated endpoints: 300 requests per minute

## Integration Guidelines

### Client Implementation Best Practices

1. **Handle cache efficiently**: Use the `cache_hit` field to show users when data is from cache vs. freshly fetched
2. **Implement error handling**: Always check the `success` field and handle errors gracefully
3. **Support different sorting options**: Allow users to sort by different criteria using the `sort_by` parameter
4. **Add retry logic**: If a provider fails, consider retrying with `force_refresh=true`

### JavaScript Example

```javascript
// Example using fetch API
async function getQuotes(sourceCountry, destCountry, sourceCurrency, destCurrency, amount, sortBy = 'best_rate') {
  const url = `http://localhost:8000/api/quotes/?source_country=${sourceCountry}&dest_country=${destCountry}&source_currency=${sourceCurrency}&dest_currency=${destCurrency}&amount=${amount}&sort_by=${sortBy}`;
  
  try {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Error: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching quotes:', error);
    throw error;
  }
}
```

## Versioning

This API follows semantic versioning. The current version is 1.0.

Future API changes:
- Minor version updates (1.1, 1.2): Non-breaking additions
- Major version updates (2.0): Breaking changes with deprecated endpoints

## Support

For API support, contact api-support@remitscout.com or open an issue on our GitHub repository. 