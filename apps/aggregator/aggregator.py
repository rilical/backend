import logging
import time
from decimal import Decimal
from typing import List, Dict, Any, Optional, Callable, Tuple
import concurrent.futures
import datetime
import random

from django.core.cache import cache
from django.conf import settings

from apps.providers.xe.integration import XEAggregatorProvider
from apps.providers.remitly.integration import RemitlyProvider
from apps.providers.ria.integration import RIAProvider
from apps.providers.wise.integration import WiseProvider
from apps.providers.transfergo.integration import TransferGoProvider
from apps.providers.xoom.integration import XoomProvider
from apps.providers.singx.integration import SingXProvider
from apps.providers.paysend.integration import PaysendProvider
from apps.providers.remitbee.integration import RemitbeeProvider
from apps.providers.instarem.integration import InstaRemProvider
from apps.providers.pangea.integration import PangeaProvider
from apps.providers.koronapay.integration import KoronaPayProvider
from apps.providers.mukuru.integration import MukuruProvider
from apps.providers.rewire.integration import RewireProvider
from apps.providers.sendwave.integration import SendwaveProvider
from apps.providers.wirebarley.integration import WireBarleyProvider
from apps.providers.orbitremit.integration import OrbitRemitProvider
from apps.providers.dahabshiil.integration import DahabshiilProvider
from apps.providers.intermex.integration import IntermexProvider
from apps.providers.placid.integration import PlacidProvider
from apps.providers.remitguru.integration import RemitGuruProvider
from apps.providers.westernunion.integration import WesternUnionProvider
from apps.providers.alansari.integration import AlAnsariProvider

logger = logging.getLogger(__name__)

# Add cache key generator function at the top level
def get_provider_quote_cache_key(provider_name, source_country, dest_country, source_currency, dest_currency, amount):
    """Generate a cache key for individual provider quotes."""
    return f"provider_quote:{provider_name}:{source_country}:{dest_country}:{source_currency}:{dest_currency}:{float(amount)}"

class Aggregator:

    PROVIDERS = [
        XEAggregatorProvider(),
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
        "RemitlyProvider": {
            "get_quote": {
                "amount": "amount",
                "source_currency": "source_currency",
                "dest_currency": "dest_currency",
                "source_country": "source_country",
                "dest_country": "dest_country"
            }
        },
        "RIAProvider": {
            "get_quote": {
                "amount": "amount",
                "source_currency": "source_currency",
                "dest_currency": "dest_currency",
                "source_country": "source_country",
                "dest_country": "dest_country",
                "payment_method": "debitCard",
                "delivery_method": "bankDeposit"
            }
        },
        "WiseProvider": {
            "get_quote": {
                "amount": "amount",
                "source_currency": "source_currency",
                "destination_currency": "dest_currency",
                "source_country": "source_country",
                "dest_country": "dest_country"
            }
        },
        "TransferGoProvider": {
            "get_quote": {
                "amount": "amount",
                "source_currency": "source_currency",
                "destination_currency": "dest_currency",
                "source_country": "source_country",
                "destination_country": "dest_country"
            }
        },
        "WesternUnionProvider": {
            "get_quote": {
                "amount": "amount",
                "source_currency": "source_currency",
                "dest_currency": "dest_currency",
                "source_country": "source_country",
                "dest_country": "dest_country"
            }
        },
        "XoomProvider": {
            "get_quote": {
                "amount": "amount",
                "source_currency": "source_currency",
                "dest_currency": "dest_currency",
                "source_country": "source_country",
                "dest_country": "dest_country"
            }
        },
        "SingXProvider": {
            "get_quote": {
                "amount": "amount",
                "source_currency": "source_currency",
                "destination_currency": "dest_currency",
                "source_country": "source_country",
                "destination_country": "dest_country"
            }
        },
        "PaysendProvider": {
            "get_quote": {
                "from_currency": "source_currency",
                "to_currency": "dest_currency",
                "from_country": "source_country",
                "to_country": "dest_country",
                "amount": "amount"
            }
        },
        "AlAnsariProvider": {
            "get_quote": {
                "amount": "amount",
                "source_currency": "source_currency",
                "dest_currency": "dest_currency",
                "source_country": "source_country",
                "dest_country": "dest_country"
            }
        },
        "RemitbeeProvider": {
            "get_quote": {
                "amount": "amount",
                "source_currency": "source_currency",
                "dest_currency": "dest_currency",
                "source_country": "source_country",
                "dest_country": "dest_country"
            }
        },
        "InstaRemProvider": {
            "get_quote": {
                "amount": "amount",
                "source_currency": "source_currency",
                "dest_currency": "dest_currency",
                "source_country": "source_country",
                "dest_country": "dest_country"
            }
        },
        "PangeaProvider": {
            "get_quote": {
                "amount": "amount",
                "source_currency": "source_currency",
                "target_currency": "dest_currency",
                "source_country": "source_country",
                "target_country": "dest_country"
            }
        },
        "KoronaPayProvider": {
            "get_quote": {
                "send_amount": "amount",
                "send_currency": "source_currency",
                "receive_currency": "dest_currency",
                "send_country": "source_country",
                "receive_country": "dest_country"
            }
        },
        "MukuruProvider": {
            "get_quote": {
                "amount": "amount",
                "source_currency": "source_currency",
                "target_country": "dest_country",
                "from_country_code": "source_country"
            }
        },
        "RewireProvider": {
            "get_quote": {
                "amount": "amount",
                "source_currency": "source_currency",
                "dest_currency": "dest_currency",
                "source_country": "source_country",
                "dest_country": "dest_country"
            }
        },
        "SendwaveProvider": {
            "get_quote": {
                "amount": "amount",
                "source_currency": "source_currency",
                "dest_currency": "dest_currency",
                "source_country": "source_country",
                "dest_country": "dest_country"
            }
        },
        "WireBarleyProvider": {
            "get_quote": {
                "amount": "amount",
                "send_currency": "source_currency",
                "receive_currency": "dest_currency",
                "send_country": "source_country",
                "receive_country": "dest_country"
            }
        },
        "OrbitRemitProvider": {
            "get_quote": {
                "amount": "amount",
                "source_currency": "source_currency",
                "dest_currency": "dest_currency",
                "source_country": "source_country",
                "dest_country": "dest_country"
            }
        },
        "DahabshiilProvider": {
            "get_quote": {
                "amount": "amount",
                "source_currency": "source_currency",
                "dest_currency": "dest_currency",
                "source_country": "source_country",
                "dest_country": "dest_country"
            }
        },
        "IntermexProvider": {
            "get_quote": {
                "send_amount": "amount",
                "send_currency": "source_currency",
                "receive_currency": "dest_currency",
                "send_country": "source_country",
                "receive_country": "dest_country"
            }
        },
        "PlacidProvider": {
            "get_quote": {
                "amount": "amount",
                "source_currency": "source_currency",
                "dest_currency": "dest_currency",
                "source_country": "source_country",
                "dest_country": "dest_country"
            }
        },
        "RemitGuruProvider": {
            "get_quote": {
                "amount": "amount",
                "source_currency": "source_currency",
                "dest_currency": "dest_currency",
                "source_country": "source_country",
                "dest_country": "dest_country"
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
            p for p in cls.PROVIDERS
            if p.__class__.__name__ not in exclude_providers
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
            from apps.aggregator.configurator import get_configured_aggregator_params
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
                    amount
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
                    "dest_country": dest_country
                }

                if (provider_name in cls.PROVIDER_PARAMS and
                    "get_quote" in cls.PROVIDER_PARAMS[provider_name]):
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
                        amount
                    )
                    try:
                        # Get TTL from settings or use default
                        provider_ttl = getattr(settings, 'PROVIDER_CACHE_TTL', 60 * 60 * 24)  # 24 hours default
                        jitter = random.randint(
                            -getattr(settings, 'JITTER_MAX_SECONDS', 60),
                            getattr(settings, 'JITTER_MAX_SECONDS', 60)
                        )
                        ttl = provider_ttl + jitter
                        
                        cache.set(cache_key, result, timeout=ttl)
                        logger.info(f"Cached result for provider {provider_id} for {ttl} seconds")
                    except Exception as cache_error:
                        logger.warning(f"Error caching result for {provider_id}: {str(cache_error)}")

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
                    "amount": float(amount)
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
                            amount
                        )
                        # Shorter TTL for failures
                        cache.set(cache_key, error_result, timeout=300)  # 5 minutes
                    except Exception:
                        pass  # Ignore caching errors for failures
                
                logger.exception(f"Error calling {provider_id}: {str(e)}")
                return error_result

        with concurrent.futures.ThreadPoolExecutor(max_workers=min(max_workers, len(providers_to_call))) as executor:
            future_to_provider = {
                executor.submit(call_provider, provider): provider
                for provider in providers_to_call
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
                q for q in all_quotes 
                if q.get("delivery_time_minutes", float("inf")) <= max_delivery_time_minutes
            ]
            
        if max_fee is not None:
            all_quotes = [
                q for q in all_quotes 
                if q.get("fee", float("inf")) <= max_fee
            ]
            
        if all_quotes and sort_by:
            if sort_by == "best_rate":
                all_quotes.sort(key=lambda q: (-(q.get("exchange_rate", 0) or 0)))
            elif sort_by == "lowest_fee":
                all_quotes.sort(key=lambda q: (q.get("fee", float("inf")) or float("inf")))
            elif sort_by == "fastest_time":
                all_quotes.sort(key=lambda q: (q.get("delivery_time_minutes", float("inf")) or float("inf")))
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
            "timestamp": datetime.datetime.now().isoformat()
        }


def sample_usage():
    from decimal import Decimal
    aggregator_result = Aggregator.get_all_quotes(
        source_country="US",
        dest_country="IN",
        source_currency="USD",
        dest_currency="INR",
        amount=Decimal("1000"),
        sort_by="best_rate"
    )

    print(f"Global success: {aggregator_result['success']}")
    print(f"Found {len(aggregator_result['results'])} quotes")

    for i, quote in enumerate(aggregator_result["results"], 1):
        if quote.get('success'):
            print(f"{i}. {quote.get('provider_id')}: rate={quote.get('exchange_rate')}, "
                  f"fee={quote.get('fee')}, delivery={quote.get('delivery_time_minutes')} min")
        else:
            print(f"{i}. {quote.get('provider_id')}: FAILED - {quote.get('error_message')}")
