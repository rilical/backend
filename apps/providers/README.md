# RemitScout Providers

This module contains integrations with various remittance service providers, enabling the RemitScout aggregator to compare rates and fees across multiple services.

## Implemented Providers

| Provider | Description | Primary Corridors | Status |
|----------|-------------|-------------------|--------|
| XE | Global currency and foreign exchange service | Global | ✅ Working |
| Remitly | Digital remittance service focused on immigrant communities | US/EU to Global | ✅ Working |
| RIA | Global money transfer company | Global | ✅ Working |
| Wise (TransferWise) | Online money transfer service | Global | ✅ Working |
| Xoom (PayPal) | PayPal's international money transfer service | US/CA to Latin America, Asia | ✅ Working |
| Paysend | Global card-to-card money transfer platform | EU/US to Global | ✅ Working |
| SingX | Singapore-based money transfer service | Singapore to Asia | ⚠️ Limited |
| TransferGo | Digital remittance service for migrants | EU to Eastern Europe, Asia | ⚠️ Limited |
| AlAnsari | UAE-based exchange and transfer service | UAE to South Asia | ⚠️ Testing |
| Remitbee | Canada-based digital remittance service | Canada to Global | ⚠️ Testing |
| InstaRem | Singapore-based cross-border payment company | Asia-Pacific | ⚠️ Testing |
| Pangea | US-based mobile money transfer service | US to Latin America | ⚠️ Testing |
| KoronaPay | Russia-based money transfer service | Russia to CIS countries | ⚠️ Testing |
| Mukuru | Africa-focused remittance provider | Africa corridors | ⚠️ Testing |
| Rewire | European digital banking service for migrants | EU to Asia, Africa | ⚠️ Testing |
| Sendwave | Mobile money transfer app focused on Africa | US/EU to Africa | ⚠️ Testing |
| WireBarley | South Korea-based global remittance service | South Korea to Global | ⚠️ Testing |
| OrbitRemit | New Zealand-based money transfer service | NZ/AU to Global | ⚠️ Testing |
| Dahabshiil | African money transfer operator | Global to Africa | ⚠️ Testing |
| Western Union | Global financial services company | Global | ❌ Pending |

## Provider Interface

All providers implement the following interface:

```python
class RemittanceProvider:
    """Base interface for all remittance service providers."""
    
    def get_quote(
        self, 
        amount: Decimal, 
        source_currency: str, 
        dest_currency: str, 
        source_country: str, 
        dest_country: str, 
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get a quote for sending money from one country to another.
        """
        pass
        
    def get_exchange_rate(
        self, 
        source_currency: str, 
        dest_currency: str, 
        source_country: str,
        dest_country: str
    ) -> float:
        """
        Get the current exchange rate between two currencies.
        """
        pass
        
    def standardize_response(
        self, 
        raw_result: Dict[str, Any], 
        provider_specific_data: bool = False
    ) -> Dict[str, Any]:
        """
        Convert provider-specific response format to a standardized format.
        """
        pass
```

## Adding a New Provider

To add a new provider:

1. Create a new directory under `apps/providers/` with the provider name (e.g., `apps/providers/newprovider/`)
2. Add the following files:
   - `__init__.py`: Expose the provider class and exceptions
   - `integration.py`: Implement the provider class with API integration
   - `exceptions.py`: Define provider-specific exceptions
   - `README.md`: Document the provider's details, API endpoints, etc.
3. Implement the required interface methods
4. Add the provider to the aggregator in `apps/aggregator/aggregator.py`
5. Add any required parameter mappings to the aggregator

## Best Practices

When implementing a provider:

1. **Robust Error Handling**: Catch and properly handle all API errors
2. **Consistent Response Format**: Ensure `standardize_response()` follows the expected format
3. **Detailed Logging**: Include logging statements for debugging
4. **Comprehensive Documentation**: Document API endpoints, rate limits, etc.
5. **API Keys Security**: Never hardcode API keys; use environment variables
6. **Mock Support**: Include support for mock responses for testing 