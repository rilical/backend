import concurrent.futures
import datetime
import logging
import random
import time
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional, Tuple

from django.conf import settings
from django.core.cache import cache

from providers.alansari.integration import AlAnsariProvider
from providers.dahabshiil.integration import DahabshiilProvider
from providers.instarem.integration import InstaRemProvider
from providers.intermex.integration import IntermexProvider
from providers.koronapay.integration import KoronaPayProvider
from providers.mukuru.integration import MukuruProvider
from providers.orbitremit.integration import OrbitRemitProvider
from providers.pangea.integration import PangeaProvider
from providers.paysend.integration import PaysendProvider
from providers.placid.integration import PlacidProvider
from providers.remitbee.integration import RemitbeeProvider
from providers.remitguru.integration import RemitGuruProvider
from providers.remitly.integration import RemitlyProvider
from providers.rewire.integration import RewireProvider
from providers.ria.integration import RIAProvider
from providers.sendwave.integration import SendwaveProvider
from providers.singx.integration import SingXProvider
from providers.transfergo.integration import TransferGoProvider
from providers.westernunion.integration import WesternUnionProvider
from providers.wirebarley.integration import WireBarleyProvider
from providers.wise.integration import WiseProvider
from providers.xe.integration import XEProvider
from providers.xoom.integration import XoomProvider

logger = logging.getLogger(__name__)


# Add cache key generator function at the top level
def get_provider_quote_cache_key(
    provider_name, source_country, dest_country, source_currency, dest_currency, amount
):
    """Generate a cache key for individual provider quotes."""
    # Ensure provider name is uppercase for consistency
    provider_name_upper = provider_name.upper()
    return f"provider_quote:{provider_name_upper}:{source_country}:{dest_country}:{source_currency}:{dest_currency}:{float(amount)}"


class Aggregator:
    PROVIDERS = [
        XEProvider(),
        RemitlyProvider(),
        RIAProvider(),
        WiseProvider(),
        TransferGoProvider(),
        WesternUnionProvider(),
        XoomProvider(),
        SingXProvider(),
        PaysendProvider(),
        AlAnsariProvider(),
        RemitbeeProvider(),
        InstaRemProvider(),
        PangeaProvider(),
        KoronaPayProvider(),
        MukuruProvider(),
        RewireProvider(),
        SendwaveProvider(),
        WireBarleyProvider(),
        OrbitRemitProvider(),
        DahabshiilProvider(),
        IntermexProvider(),
        PlacidProvider(),
        RemitGuruProvider(),
    ]

    PROVIDER_PARAMS = {
        "REMITLYPROVIDER": {
            "get_quote": {
                "amount": "amount",
                "source_currency": "source_currency",
                "dest_currency": "dest_currency",
                "source_country": "source_country",
                "dest_country": "dest_country",
            }
        },
        "RIAPROVIDER": {
            "get_quote": {
                "amount": "amount",
                "source_currency": "source_currency",
                "dest_currency": "dest_currency",
                "source_country": "source_country",
                "dest_country": "dest_country",
                "payment_method": "debitCard",
                "delivery_method": "bankDeposit",
            }
        },
        "WISEPROVIDER": {
            "get_quote": {
                "amount": "amount",
                "source_currency": "source_currency",
                "destination_currency": "dest_currency",
                "source_country": "source_country",
                "dest_country": "dest_country",
            }
        },
        "TransferGoProvider": {
            "get_quote": {
                "amount": "amount",
                "source_currency": "source_currency",
                "destination_currency": "dest_currency",
                "source_country": "source_country",
                "destination_country": "dest_country",
            }
        },
        "WesternUnionProvider": {
            "get_quote": {
                "amount": "amount",
                "source_currency": "source_currency",
                "dest_currency": "dest_currency",
                "source_country": "source_country",
                "dest_country": "dest_country",
            }
        },
        "XoomProvider": {
            "get_quote": {
                "amount": "amount",
                "source_currency": "source_currency",
                "dest_currency": "dest_currency",
                "source_country": "source_country",
                "dest_country": "dest_country",
            }
        },
        "SingXProvider": {
            "get_quote": {
                "amount": "amount",
                "source_currency": "source_currency",
                "destination_currency": "dest_currency",
                "source_country": "source_country",
                "destination_country": "dest_country",
            }
        },
        "PaysendProvider": {
            "get_quote": {
                "from_currency": "source_currency",
                "to_currency": "dest_currency",
                "from_country": "source_country",
                "to_country": "dest_country",
                "amount": "amount",
            }
        },
        "AlAnsariProvider": {
            "get_quote": {
                "amount": "amount",
                "source_currency": "source_currency",
                "dest_currency": "dest_currency",
                "source_country": "source_country",
                "dest_country": "dest_country",
            }
        },
        "RemitbeeProvider": {
            "get_quote": {
                "amount": "amount",
                "source_currency": "source_currency",
                "dest_currency": "dest_currency",
                "source_country": "source_country",
                "dest_country": "dest_country",
            }
        },
        "InstaRemProvider": {
            "get_quote": {
                "amount": "amount",
                "source_currency": "source_currency",
                "dest_currency": "dest_currency",
                "source_country": "source_country",
                "dest_country": "dest_country",
            }
        },
        "PangeaProvider": {
            "get_quote": {
                "amount": "amount",
                "source_currency": "source_currency",
                "target_currency": "dest_currency",
                "source_country": "source_country",
                "target_country": "dest_country",
            }
        },
        "KoronaPayProvider": {
            "get_quote": {
                "send_amount": "amount",
                "send_currency": "source_currency",
                "receive_currency": "dest_currency",
                "send_country": "source_country",
                "receive_country": "dest_country",
            }
        },
        "MukuruProvider": {
            "get_quote": {
                "amount": "amount",
                "source_currency": "source_currency",
                "target_country": "dest_country",
                "from_country_code": "source_country",
            }
        },
        "RewireProvider": {
            "get_quote": {
                "amount": "amount",
                "source_currency": "source_currency",
                "dest_currency": "dest_currency",
                "source_country": "source_country",
                "dest_country": "dest_country",
            }
        },
        "SendwaveProvider": {
            "get_quote": {
                "amount": "amount",
                "source_currency": "source_currency",
                "dest_currency": "dest_currency",
                "source_country": "source_country",
                "dest_country": "dest_country",
            }
        },
        "WireBarleyProvider": {
            "get_quote": {
                "amount": "amount",
                "send_currency": "source_currency",
                "receive_currency": "dest_currency",
                "send_country": "source_country",
                "receive_country": "dest_country",
            }
        },
        "OrbitRemitProvider": {
            "get_quote": {
                "amount": "amount",
                "source_currency": "source_currency",
                "dest_currency": "dest_currency",
                "source_country": "source_country",
                "dest_country": "dest_country",
            }
        },
        "DahabshiilProvider": {
            "get_quote": {
                "amount": "amount",
                "source_currency": "source_currency",
                "dest_currency": "dest_currency",
                "source_country": "source_country",
                "dest_country": "dest_country",
            }
        },
        "IntermexProvider": {
            "get_quote": {
                "send_amount": "amount",
                "send_currency": "source_currency",
                "receive_currency": "dest_currency",
                "send_country": "source_country",
                "receive_country": "dest_country",
            }
        },
        "PlacidProvider": {
            "get_quote": {
                "amount": "amount",
                "source_currency": "source_currency",
                "dest_currency": "dest_currency",
                "source_country": "source_country",
                "dest_country": "dest_country",
            }
        },
        "RemitGuruProvider": {
            "get_quote": {
                "amount": "amount",
                "source_currency": "source_currency",
                "dest_currency": "dest_currency",
                "source_country": "source_country",
                "dest_country": "dest_country",
            }
        },
    }

    @classmethod
    def get_all_quotes(
        cls,
        source_country: str,
        dest_country: str,
        source_currency: str,
        dest_currency: str,
        amount: Decimal,
        sort_by: Optional[str] = "best_rate",
        exclude_providers: Optional[List[str]] = None,
        max_workers: int = 10,
        filter_fn: Optional[Callable[[Dict[str, Any]], bool]] = None,
        max_delivery_time_minutes: Optional[int] = None,
        max_fee: Optional[float] = None,
        use_cache: bool = True,  # New parameter to control caching
    ) -> Dict[str, Any]:
        exclude_providers = exclude_providers or []
        providers_to_call = [
            p for p in cls.PROVIDERS if p.__class__.__name__ not in exclude_providers
        ]

        logger.info(
            f"Aggregator: Starting quotes for {amount:.2f} {source_currency} -> {dest_currency}, "
            f"corridor {source_country}->{dest_country}"
        )
        logger.info(f"Total providers to call: {len(providers_to_call)}")

        start_time = time.time()
        all_quotes = []
        all_provider_results = []

        try:
            from aggregator.configurator import get_configured_aggregator_params

            config_params = get_configured_aggregator_params()
            timeout = config_params.get("timeout", 20)
        except ImportError:
            timeout = 20
            logger.warning("Could not import configurator, using default timeout")

        def call_provider(provider):
            provider_name = provider.__class__.__name__
            provider_id = getattr(provider, "provider_id", provider_name)

            # Check cache first if caching is enabled
            if use_cache:
                cache_key = get_provider_quote_cache_key(
                    provider_name,
                    source_country,
                    dest_country,
                    source_currency,
                    dest_currency,
                    amount,
                )
                cached_result = cache.get(cache_key)
                if cached_result:
                    logger.info(f"Cache hit for provider {provider_id}")
                    if cached_result.get("success", False):
                        all_quotes.append(cached_result)
                    return cached_result

            try:
                provider_params = {
                    "amount": amount,
                    "source_currency": source_currency,
                    "dest_currency": dest_currency,
                    "source_country": source_country,
                    "dest_country": dest_country,
                }

                if (
                    provider_name in cls.PROVIDER_PARAMS
                    and "get_quote" in cls.PROVIDER_PARAMS[provider_name]
                ):
                    param_map = cls.PROVIDER_PARAMS[provider_name]["get_quote"]
                    mapped_params = {}
                    for target_param, source_param in param_map.items():
                        mapped_params[target_param] = provider_params.get(source_param)
                    provider_params = mapped_params

                logger.info(f"Calling {provider_id}.get_quote(...) with {provider_params}")
                result = provider.get_quote(**provider_params)

                if "provider_id" not in result:
                    result["provider_id"] = provider_id

                # Store successful results in cache with TTL and jitter
                if use_cache and result.get("success", False):
                    cache_key = get_provider_quote_cache_key(
                        provider_name,
                        source_country,
                        dest_country,
                        source_currency,
                        dest_currency,
                        amount,
                    )
                    try:
                        # Get TTL from settings or use default
                        provider_ttl = getattr(
                            settings, "PROVIDER_CACHE_TTL", 60 * 60 * 24
                        )  # 24 hours default
                        jitter = random.randint(
                            -getattr(settings, "JITTER_MAX_SECONDS", 60),
                            getattr(settings, "JITTER_MAX_SECONDS", 60),
                        )
                        ttl = provider_ttl + jitter

                        cache.set(cache_key, result, timeout=ttl)
                        logger.info(f"Cached result for provider {provider_id} for {ttl} seconds")
                    except Exception as cache_error:
                        logger.warning(
                            f"Error caching result for {provider_id}: {str(cache_error)}"
                        )

                if result.get("success", False):
                    all_quotes.append(result)

                return result

            except Exception as e:
                error_result = {
                    "success": False,
                    "provider_id": provider_id,
                    "error_message": f"Exception: {str(e)}",
                    "source_currency": source_currency,
                    "destination_currency": dest_currency,
                    "source_country": source_country,
                    "dest_country": dest_country,
                    "amount": float(amount),
                }

                # Cache failures briefly to prevent hammering APIs that are down
                if use_cache:
                    try:
                        cache_key = get_provider_quote_cache_key(
                            provider_name,
                            source_country,
                            dest_country,
                            source_currency,
                            dest_currency,
                            amount,
                        )
                        # Shorter TTL for failures
                        cache.set(cache_key, error_result, timeout=300)  # 5 minutes
                    except Exception:
                        pass  # Ignore caching errors for failures

                logger.exception(f"Error calling {provider_id}: {str(e)}")
                return error_result

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=min(max_workers, len(providers_to_call))
        ) as executor:
            future_to_provider = {
                executor.submit(call_provider, provider): provider for provider in providers_to_call
            }

            for future in concurrent.futures.as_completed(future_to_provider, timeout=timeout):
                provider = future_to_provider[future]
                provider_name = provider.__class__.__name__
                try:
                    result = future.result()
                    if result:
                        if provider_name == "RemitGuruProvider":
                            logger.info(f"RemitGuru result from future: {result}")

                        all_provider_results.append(result)
                        if result.get("success", False):
                            all_quotes.append(result)
                except Exception as exc:
                    logger.error(f"Provider {provider_name} generated an exception: {exc}")

        if filter_fn:
            all_quotes = [q for q in all_quotes if filter_fn(q)]

        if max_delivery_time_minutes is not None:
            all_quotes = [
                q
                for q in all_quotes
                if q.get("delivery_time_minutes", float("inf")) <= max_delivery_time_minutes
            ]

        if max_fee is not None:
            all_quotes = [q for q in all_quotes if q.get("fee", float("inf")) <= max_fee]

        if all_quotes and sort_by:
            if sort_by == "best_rate":
                all_quotes.sort(key=lambda q: (-(q.get("exchange_rate", 0) or 0)))
            elif sort_by == "lowest_fee":
                all_quotes.sort(key=lambda q: (q.get("fee", float("inf")) or float("inf")))
            elif sort_by == "fastest_time":
                all_quotes.sort(
                    key=lambda q: (q.get("delivery_time_minutes", float("inf")) or float("inf"))
                )
            elif sort_by == "best_value":

                def value_score(quote):
                    rate_score = quote.get("exchange_rate", 0) or 0
                    fee_score = 100 - (quote.get("fee", 0) or 0) * 10
                    time_score = 100 - min(100, ((quote.get("delivery_time_minutes", 0) or 0) / 30))
                    return rate_score * 0.5 + fee_score * 0.3 + time_score * 0.2

                all_quotes.sort(key=value_score, reverse=True)

        logger.info(f"Final quotes count: {len(all_quotes)}")
        for i, quote in enumerate(all_quotes):
            logger.info(f"Quote {i+1}: {quote.get('provider_id')} - {quote.get('success')}")

        end_time = time.time()
        execution_time = end_time - start_time

        return {
            "success": len(all_quotes) > 0,
            "results": all_quotes,
            "all_results": all_provider_results,
            "execution_time": execution_time,
            "providers_called": len(providers_to_call),
            "successful_providers": len(all_quotes),
            "timestamp": datetime.datetime.now().isoformat(),
        }

def get_cached_aggregated_rates(
    send_amount: Decimal,
    send_currency: str,
    receive_country: str,
    receive_currency: Optional[str] = None,
    cache_timeout: int = 3600,
) -> List[Dict[str, Any]]:
    """
    Get aggregated remittance rates from all available providers with caching.

    This function fetches quotes from all registered providers for the specified
    money transfer parameters and returns a consolidated list of standardized quotes.
    Results are cached for improved performance.

    Args:
        send_amount: The amount to send in the source currency
        send_currency: The source currency code (e.g., 'USD', 'EUR')
        receive_country: The destination country code (e.g., 'MX', 'IN')
        receive_currency: Optional destination currency code. If not provided,
                          the default currency for the destination country will be used.
        cache_timeout: Cache TTL in seconds (defaults to 1 hour)

    Returns:
        A list of standardized quote dictionaries from all available providers,
        sorted by exchange rate (best first). Each quote contains:
        - provider_id: Unique identifier of the provider
        - provider_name: Human-readable name of the provider
        - exchange_rate: The exchange rate offered
        - fee: The fee charged for the transfer
        - amount_received: The amount that will be received
        - delivery_time_minutes: Estimated delivery time in minutes
        - source_currency: Source currency code
        - destination_currency: Destination currency code
        - success: Boolean indicating if the quote was successfully retrieved

    Example:
        >>> quotes = get_cached_aggregated_rates(
        ...     send_amount=Decimal("1000.00"),
        ...     send_currency="USD",
        ...     receive_country="MX"
        ... )
        >>> print(f"Found {len(quotes)} quotes")
        Found 15 quotes
    """
    # Generate a cache key based on the parameters
    cache_key = f"aggregated_rates:{send_currency}:{receive_country}:{float(send_amount)}"
    if receive_currency:
        cache_key += f":{receive_currency}"
    
    # Try to get cached results first
    cached_results = cache.get(cache_key)
    if cached_results and cache_timeout > 0:
        logger.info(f"Using cached aggregated rates: {cache_key}")
        return cached_results
    
    # Cache miss or force refresh, get fresh quotes
    logger.info(f"Cache miss for {cache_key}, fetching fresh quotes")
    
    # Determine the destination currency if not provided
    if not receive_currency:
        # This would use a utility function to get the default currency for the country
        # For now we'll just use a placeholder
        if "utils" in globals() and hasattr(globals()["utils"], "get_default_currency_for_country"):
            receive_currency = utils.get_default_currency_for_country(receive_country)
        else:
            # Fallback to USD for now (this should be replaced with proper logic)
            # In a real implementation, this would look up the default currency
            receive_currency = "USD"
    
    # Get fresh quotes from the aggregator
    results = Aggregator.get_all_quotes(
        source_country="US",  # This is hardcoded for now but should be determined based on currency
        dest_country=receive_country,
        source_currency=send_currency,
        dest_currency=receive_currency,
        amount=send_amount,
        sort_by="best_rate",  # Sort by best exchange rate by default
        use_cache=False,  # Don't use provider-level caching since we're caching the whole result
    )
    
    # Extract just the standardized quotes from the response
    quotes = results.get("quotes", [])
    
    # Only cache successful results that have at least one quote
    if quotes and any(q.get("success", False) for q in quotes):
        # Add some jitter to prevent thundering herd
        jitter = random.randint(-60, 60)
        actual_timeout = max(1, cache_timeout + jitter)  # Ensure timeout is at least 1 second
        
        # Cache the results
        cache.set(cache_key, quotes, timeout=actual_timeout)
        logger.info(f"Cached fresh aggregated rates for {cache_key}, TTL={actual_timeout}s")
    
    return quotes
