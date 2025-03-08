import logging
from decimal import Decimal
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone

from .factory import ProviderFactory
from .base.provider import RemittanceProvider
from .models import ExchangeRate
from .utils.country_currency_standards import validate_corridor

logger = logging.getLogger(__name__)

def get_cached_aggregated_rates(
    send_amount: Decimal,
    source_country: str,      # ISO-3166-1 alpha-2 (e.g., "AE")
    source_currency: str,     # ISO-4217 (e.g., "AED")
    dest_country: str,        # ISO-3166-1 alpha-2 (e.g., "IN")
    dest_currency: str,       # ISO-4217 (e.g., "INR")
    cache_timeout: int = 60 * 60 * 24  # 1 day in seconds
) -> list:
    """
    Main aggregator function that:
    1. Checks cache for existing results using standardized codes
    2. If not in cache, calls each provider with ISO standard codes
    3. Stores aggregated results in cache with 1-day expiry
    4. Returns the final list of quotes
    
    Args:
        send_amount: Amount to send
        source_country: Source country code (ISO-3166-1 alpha-2)
        source_currency: Source currency code (ISO-4217)
        dest_country: Destination country code (ISO-3166-1 alpha-2)
        dest_currency: Destination currency code (ISO-4217)
        cache_timeout: Cache timeout in seconds (default: 1 day)
        
    Returns:
        List of quotes from all available providers
    """
    # Standardize and validate inputs
    source_country = source_country.upper()
    source_currency = source_currency.upper()
    dest_country = dest_country.upper()
    dest_currency = dest_currency.upper()
    
    # Validate corridor using ISO standards
    is_valid, error_msg = validate_corridor(
        source_country=source_country,
        source_currency=source_currency,
        dest_country=dest_country,
        dest_currency=dest_currency
    )
    
    if not is_valid:
        logger.error(f"Invalid corridor: {error_msg}")
        return []

    # Create a unique key with version prefix for easy cache invalidation if needed
    cache_version = "v1"
    cache_key = f"{cache_version}_aggregated_rates_{send_amount}_{source_country}_{source_currency}_{dest_country}_{dest_currency}".upper()

    # 1. Check if cached
    cached_data = cache.get(cache_key)
    if cached_data:
        logger.info(f"Aggregator: Using cached results for {cache_key} (valid for 24 hours)")
        return cached_data["results"]

    # 2. If not in cache, call each provider
    logger.info(
        f"Aggregator: No cache found, fetching new quotes for corridor "
        f"{source_country}-{source_currency} -> {dest_country}-{dest_currency}"
    )
    providers = ProviderFactory.list_providers()
    results = []
    timestamp = timezone.now()

    for provider_name in providers:
        provider_instance = ProviderFactory.get_provider(provider_name)
        try:
            quote = provider_instance.get_exchange_rate(
                amount=send_amount,
                source_country=source_country,
                source_currency=source_currency,
                dest_country=dest_country,
                dest_currency=dest_currency
            )
            
            if quote and quote.get("success", False):
                # Format the quote to ensure consistent structure
                formatted_quote = {
                    "success": True,
                    "provider": provider_name,
                    "send_amount": float(send_amount),
                    "source_country": source_country,
                    "dest_country": dest_country,
                    "source_currency": source_currency,
                    "dest_currency": dest_currency,
                    "receive_amount": float(quote.get("receive_amount", 0)),
                    "exchange_rate": float(quote.get("exchange_rate", 0)),
                    "fee": float(quote.get("fee", 0)),
                    "delivery_time_minutes": quote.get("delivery_time_minutes"),
                    "error": None,
                    "quote_timestamp": timestamp.isoformat()
                }
                results.append(formatted_quote)

                # Store to ExchangeRate model for historical tracking
                ExchangeRate.objects.create(
                    provider=provider_name,
                    send_amount=send_amount,
                    send_currency=source_currency,
                    receive_country=dest_country,
                    exchange_rate=Decimal(str(formatted_quote["exchange_rate"])),
                    transfer_fee=Decimal(str(formatted_quote.get("fee", 0))),
                    delivery_time=f"{formatted_quote['delivery_time_minutes']} minutes" if formatted_quote.get("delivery_time_minutes") else "N/A",
                    timestamp=timestamp
                )
            else:
                error_msg = quote.get("error_message") if quote else "No quote available"
                logger.warning(f"Provider {provider_name} returned no quote: {error_msg}")
                results.append({
                    "success": False,
                    "provider": provider_name,
                    "source_country": source_country,
                    "dest_country": dest_country,
                    "source_currency": source_currency,
                    "dest_currency": dest_currency,
                    "error": error_msg,
                    "quote_timestamp": timestamp.isoformat()
                })
        except Exception as e:
            logger.error(f"Error calling {provider_name}: {str(e)}", exc_info=True)
            results.append({
                "success": False,
                "provider": provider_name,
                "source_country": source_country,
                "dest_country": dest_country,
                "source_currency": source_currency,
                "dest_currency": dest_currency,
                "error": str(e),
                "quote_timestamp": timestamp.isoformat()
            })

    # 3. Sort results by total cost (fee + exchange rate markup)
    def total_cost(quote):
        if not quote.get("success"):
            return float('inf')
        return quote.get("fee", 0)
    
    results.sort(key=total_cost)

    # 4. Cache the final result with metadata
    cache_data = {
        "results": results,
        "cached_at": timestamp.isoformat(),
        "expires_at": (timestamp + timezone.timedelta(seconds=cache_timeout)).isoformat(),
        "corridor": {
            "source_country": source_country,
            "dest_country": dest_country,
            "source_currency": source_currency,
            "dest_currency": dest_currency,
            "amount": float(send_amount)
        }
    }
    
    # Use pipeline to set cache atomically
    pipe = cache.client.pipeline()
    pipe.set(cache_key, cache_data, timeout=cache_timeout)
    pipe.execute()

    return results