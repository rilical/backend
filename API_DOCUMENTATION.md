# RemitScout API Documentation

## Base URL
`http://localhost:8000/` (Development)

## Authentication
The API is currently public and does not require authentication.

## Endpoints

### Get Remittance Quotes
`GET /api/quotes/`

Query Parameters:
- `source_country` (required): ISO-3166-1 alpha-2 country code (e.g., "US")
- `dest_country` (required): ISO-3166-1 alpha-2 country code (e.g., "MX")
- `source_currency` (required): ISO-4217 currency code (e.g., "USD")
- `dest_currency` (required): ISO-4217 currency code (e.g., "MXN")
- `amount` (required): Decimal amount to send (e.g., "1000.00")

Example Request:
```
GET /api/quotes/?source_country=US&dest_country=MX&source_currency=USD&dest_currency=MXN&amount=1000
```

Example Response:
```json
{
  "all_results": [...],  // All results, including failed quotes
  "results": [           // Only successful quotes
    {
      "provider_id": "xoom",
      "provider_name": "Xoom",
      "source_country": "US",
      "destination_country": "MX",
      "source_currency": "USD",
      "destination_currency": "MXN",
      "source_amount": 1000.0,
      "destination_amount": 19946.0,
      "exchange_rate": 19.9464,
      "fee": 0.0,
      "payment_method": "PayPal balance",
      "delivery_method": "Bank Deposit",
      "delivery_time_minutes": 1440,
      "fixed_delivery_time": "Within 24 hours",
      "success": true,
      "available_payment_methods": [...]
    },
    // More results...
  ],
  "timestamp": "2025-03-10T20:04:31.649338+00:00",
  "cache_hit": false,
  "filters_applied": {
    "sort_by": "best_rate",
    "max_delivery_time_minutes": null,
    "max_fee": null
  }
}
```

### List Available Providers
`GET /api/providers/`

Example Response:
```json
{
  "providers": [
    {
      "id": "wise",
      "name": "Wise (TransferWise)",
      "url": "https://wise.com"
    },
    {
      "id": "xoom",
      "name": "Xoom (PayPal)",
      "url": "https://xoom.com"
    },
    // More providers...
  ]
}
```

## Frontend Integration Guidelines

### 1. Making API Requests
Use standard HTTP clients like Axios, Fetch API, or any other HTTP client library:

```javascript
// Example using fetch
async function getQuotes(sourceCountry, destCountry, sourceCurrency, destCurrency, amount) {
  const url = `http://localhost:8000/api/quotes/?source_country=${sourceCountry}&dest_country=${destCountry}&source_currency=${sourceCurrency}&dest_currency=${destCurrency}&amount=${amount}`;
  
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

### 2. Displaying Quotes
Sort and display quotes based on different criteria (exchange rate, fees, delivery time):

```javascript
// Example of sorting quotes by exchange rate
function displayQuotesByExchangeRate(quotes) {
  const sortedQuotes = quotes.sort((a, b) => b.exchange_rate - a.exchange_rate);
  
  // Render the sorted quotes in your UI
  sortedQuotes.forEach(quote => {
    // Create UI elements for each quote
  });
}
```

### 3. Handling Cache Hits
The API uses caching to improve performance. When `cache_hit` is `true`, the data came from the cache.

### 4. Error Handling
Check for the `success` field in each quote to determine if the provider successfully returned a quote. 