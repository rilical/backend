"""
Views for the quotes API.

This module defines the API views that handle quote retrieval, caching,
and response formatting in the RemitScout platform.

Version: 1.0
"""
import json
import logging
import random
from decimal import Decimal, InvalidOperation

import redis
from django.conf import settings
from django.core.cache import cache, caches
from django.utils import timezone
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from aggregator.aggregator import Aggregator

from .cache_utils import cache_corridor_rate_data, get_quotes_from_corridor_rates
from .key_generators import get_corridor_cache_key, get_quote_cache_key
from .models import FeeQuote, Provider, QuoteQueryLog
from .utils import transform_quotes_response

logger = logging.getLogger(__name__)


@extend_schema_view(
    get=extend_schema(
        summary="Get quotes from specific providers",
        description=(
            "Retrieves quotes for a specific money transfer corridor from one or more providers. "
            "Results include exchange rates, fees, and estimated delivery times. "
            "Multi-level caching is implemented for performance."
        ),
        parameters=[
            OpenApiParameter(
                name="source_country", 
                type=str, 
                location=OpenApiParameter.QUERY,
                description="Source country code (e.g., US, GB, CA)",
                required=True,
                examples=[
                    OpenApiExample("United States", value="US"),
                    OpenApiExample("United Kingdom", value="GB"),
                ]
            ),
            OpenApiParameter(
                name="dest_country", 
                type=str, 
                location=OpenApiParameter.QUERY,
                description="Destination country code (e.g., MX, IN, PH)",
                required=True,
                examples=[
                    OpenApiExample("Mexico", value="MX"),
                    OpenApiExample("India", value="IN"),
                ]
            ),
            OpenApiParameter(
                name="source_currency", 
                type=str, 
                location=OpenApiParameter.QUERY,
                description="Source currency code (e.g., USD, GBP, CAD)",
                required=True,
                examples=[
                    OpenApiExample("US Dollar", value="USD"),
                    OpenApiExample("British Pound", value="GBP"),
                ]
            ),
            OpenApiParameter(
                name="dest_currency", 
                type=str, 
                location=OpenApiParameter.QUERY,
                description="Destination currency code (e.g., MXN, INR, PHP)",
                required=True,
                examples=[
                    OpenApiExample("Mexican Peso", value="MXN"),
                    OpenApiExample("Indian Rupee", value="INR"),
                ]
            ),
            OpenApiParameter(
                name="amount", 
                type=float, 
                location=OpenApiParameter.QUERY,
                description="Amount to send in source currency",
                required=True,
                examples=[
                    OpenApiExample("Standard Amount", value=1000.00),
                ]
            ),
            OpenApiParameter(
                name="sort_by", 
                type=str, 
                location=OpenApiParameter.QUERY,
                description="How to sort the results",
                required=False,
                default="best_rate",
                enum=["best_rate", "lowest_fee", "fastest", "value_score"],
                examples=[
                    OpenApiExample("Best Exchange Rate", value="best_rate"),
                    OpenApiExample("Lowest Fee", value="lowest_fee"),
                    OpenApiExample("Fastest Delivery", value="fastest"),
                    OpenApiExample("Best Value", value="value_score"),
                ]
            ),
            OpenApiParameter(
                name="force_refresh", 
                type=bool, 
                location=OpenApiParameter.QUERY,
                description="Whether to force refresh cached data",
                required=False,
                default=False,
            ),
        ],
        responses={
            200: OpenApiResponse(
                description="Quotes retrieved successfully",
                examples=[
                    OpenApiExample(
                        "Successful Response",
                        summary="Example of successful quotes response",
                        value={
                            "success": True,
                            "timestamp": "2023-09-15T12:34:56.789Z",
                            "request": {
                                "source_country": "US",
                                "dest_country": "MX",
                                "source_currency": "USD",
                                "dest_currency": "MXN",
                                "amount": 1000.00
                            },
                            "filters_applied": {
                                "sort_by": "best_rate"
                            },
                            "quotes": [
                                {
                                    "provider_id": "xe",
                                    "provider_name": "XE Money Transfer",
                                    "logo_url": "https://example.com/xe-logo.png",
                                    "exchange_rate": 17.85,
                                    "fee": 4.99,
                                    "amount_received": 17850.00,
                                    "amount_sent": 1000.00,
                                    "delivery_time_minutes": 60,
                                    "delivery_time_display": "1 hour",
                                    "source_currency": "USD",
                                    "destination_currency": "MXN",
                                    "success": True
                                },
                                {
                                    "provider_id": "wise",
                                    "provider_name": "Wise",
                                    "logo_url": "https://example.com/wise-logo.png",
                                    "exchange_rate": 17.82,
                                    "fee": 8.50,
                                    "amount_received": 17820.00,
                                    "amount_sent": 1000.00,
                                    "delivery_time_minutes": 180,
                                    "delivery_time_display": "3 hours",
                                    "source_currency": "USD",
                                    "destination_currency": "MXN",
                                    "success": True
                                }
                            ],
                            "count": 2,
                            "cache_hit": False
                        }
                    )
                ]
            ),
            400: OpenApiResponse(
                description="Invalid parameters",
                examples=[
                    OpenApiExample(
                        "Missing Parameters",
                        value={
                            "error": "Missing required parameters. Please provide source_country, dest_country, source_currency, dest_currency, and amount."
                        }
                    ),
                    OpenApiExample(
                        "Invalid Amount",
                        value={
                            "error": "Invalid amount. Please provide a valid positive number."
                        }
                    )
                ]
            ),
            500: OpenApiResponse(
                description="Server error",
                examples=[
                    OpenApiExample(
                        "Error Response",
                        value={
                            "error": "An error occurred: Internal server error"
                        }
                    )
                ]
            )
        },
        tags=["Quotes"],
    )
)
class QuoteAPIView(APIView):
    """
    API endpoint to fetch remittance quotes from multiple providers.

    This endpoint allows clients to request quotes for a specific money transfer
    corridor (source country to destination country) with a specified amount.
    It returns sorted quotes from various providers with detailed price and
    delivery information.

    The endpoint implements a multi-level caching strategy to ensure fast response
    times while maintaining data freshness. Results can be sorted by different
    criteria and filtered based on various parameters.

    This is a public endpoint - no authentication required.

    Version: 1.0
    """

    permission_classes = [AllowAny]

    def get(self, request):
        """
        Get quotes for a specific corridor and amount.

        Retrieves quotes from multiple remittance providers for the specified
        parameters, applying caching, sorting, and filtering as requested.

        Returns:
            Response: A Django REST framework response object containing
                     the quotes and metadata.
        """
        try:
            source_country = request.query_params.get("source_country")
            dest_country = request.query_params.get("dest_country")
            source_currency = request.query_params.get("source_currency")
            dest_currency = request.query_params.get("dest_currency")
            amount = request.query_params.get("amount")
            sort_by = request.query_params.get("sort_by", "best_rate")
            force_refresh = request.query_params.get("force_refresh", "false").lower() == "true"

            if not all([source_country, dest_country, source_currency, dest_currency, amount]):
                return Response(
                    {
                        "error": "Missing required parameters. Please provide source_country, dest_country, source_currency, dest_currency, and amount."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                amount_decimal = Decimal(amount)
                if amount_decimal <= 0:
                    raise ValueError("Amount must be positive")
            except (InvalidOperation, ValueError):
                return Response(
                    {"error": "Invalid amount. Please provide a valid positive number."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            self._log_query(
                source_country,
                dest_country,
                source_currency,
                dest_currency,
                amount_decimal,
                request,
            )

            if force_refresh:
                logger.info("Force refresh requested, bypassing all caches")
                return self._fetch_and_return_fresh_quotes(
                    source_country,
                    dest_country,
                    source_currency,
                    dest_currency,
                    amount_decimal,
                    sort_by,
                    cache_results=True,
                )

            cache_key = get_quote_cache_key(
                source_country,
                dest_country,
                source_currency,
                dest_currency,
                amount_decimal,
            )

            print(f"DEBUG: Looking for cache key: {cache_key}")

            exact_match = None

            exact_match = cache.get(cache_key)
            print(f"DEBUG: Django cache.get result: {exact_match is not None}")

            if not exact_match:
                try:
                    r = redis.Redis.from_url(settings.CACHES["default"]["LOCATION"])
                    redis_key_json = f"{settings.CACHES['default']['KEY_PREFIX']}:json:{cache_key}"
                    print(f"DEBUG: Direct Redis lookup for JSON key: {redis_key_json}")
                    redis_match = r.get(redis_key_json)
                    print(f"DEBUG: Redis JSON lookup result: {redis_match is not None}")

                    if redis_match:
                        try:
                            exact_match = json.loads(redis_match)
                            print(f"DEBUG: Successfully deserialized Redis JSON data")
                        except json.JSONDecodeError as e:
                            print(f"DEBUG: Error deserializing Redis JSON data: {str(e)}")
                except Exception as e:
                    print(f"DEBUG: Error in direct Redis JSON lookup: {str(e)}")

            if exact_match:
                exact_match["cache_hit"] = True
                logger.info(f"Exact cache hit for key: {cache_key}")
                return Response(exact_match)

            corridor_key = get_corridor_cache_key(source_country, dest_country)
            corridor_available = cache.get(corridor_key)

            if corridor_available is not None and not corridor_available:
                logger.info(
                    f"Skipping known unavailable corridor: {source_country}->{dest_country}"
                )
                return Response(
                    {
                        "success": False,
                        "error": "This corridor is not currently supported by any provider.",
                        "source_country": source_country,
                        "dest_country": dest_country,
                        "cache_hit": True,
                    }
                )

            corridor_rate_response = get_quotes_from_corridor_rates(
                source_country,
                dest_country,
                source_currency,
                dest_currency,
                amount_decimal,
            )

            if corridor_rate_response:
                logger.info(
                    f"Using cached corridor rates to calculate quotes for amount: {amount_decimal}"
                )

                self._sort_quotes(corridor_rate_response.get("quotes", []), sort_by)

                if "filters_applied" not in corridor_rate_response:
                    corridor_rate_response["filters_applied"] = {}
                corridor_rate_response["filters_applied"]["sort_by"] = sort_by

                jitter = random.randint(-settings.JITTER_MAX_SECONDS, settings.JITTER_MAX_SECONDS)
                ttl = settings.QUOTE_CACHE_TTL + jitter
                cache.set(cache_key, corridor_rate_response, timeout=ttl)

                logger.info(
                    f"Cached calculated response for amount {amount_decimal} with key: {cache_key}"
                )
                return Response(corridor_rate_response)

            logger.info(f"No cache hits, fetching fresh quotes from aggregator")
            return self._fetch_and_return_fresh_quotes(
                source_country,
                dest_country,
                source_currency,
                dest_currency,
                amount_decimal,
                sort_by,
                cache_results=True,
            )

        except Exception as e:
            logger.exception(f"Error in QuoteAPIView: {str(e)}")
            return Response(
                {"error": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _fetch_and_return_fresh_quotes(
        self,
        source_country,
        dest_country,
        source_currency,
        dest_currency,
        amount_decimal,
        sort_by,
        cache_results=True,
    ):
        """Fetch fresh quotes from the aggregator and cache appropriately"""
        logger.info(
            f"Fetching quotes from aggregator for {amount_decimal} {source_currency} -> {dest_currency}"
        )
        raw_response = self._get_quotes_from_aggregator(
            source_country,
            dest_country,
            source_currency,
            dest_currency,
            amount_decimal,
            sort_by,
        )

        response_data = self._transform_response(
            raw_response,
            source_country,
            dest_country,
            source_currency,
            dest_currency,
            amount_decimal,
            sort_by,
        )

        if not cache_results:
            return Response(response_data)

        all_quotes = response_data.get("quotes", [])
        successful_quotes = [q for q in all_quotes if q.get("success", False)]
        has_quotes = len(successful_quotes) > 0

        corridor_key = get_corridor_cache_key(source_country, dest_country)
        corridor_ttl = settings.CORRIDOR_CACHE_TTL
        cache.set(corridor_key, has_quotes, timeout=corridor_ttl)

        if has_quotes:
            specific_key = get_quote_cache_key(
                source_country,
                dest_country,
                source_currency,
                dest_currency,
                amount_decimal,
            )
            jitter = random.randint(-settings.JITTER_MAX_SECONDS, settings.JITTER_MAX_SECONDS)
            ttl = settings.QUOTE_CACHE_TTL + jitter

            if "cache_hit" in response_data:
                response_data["cache_hit"] = False
            else:
                response_data.update({"cache_hit": False})

            print(f"DEBUG: Setting cache with key: {specific_key}, TTL: {ttl}")

            try:
                cache.set(specific_key, response_data, timeout=ttl)
                print(f"DEBUG: Django cache.set for key: {specific_key}")

                r = redis.Redis.from_url(settings.CACHES["default"]["LOCATION"])

                redis_key_original = f"{settings.CACHES['default']['KEY_PREFIX']}:1:{specific_key}"
                redis_key_json = f"{settings.CACHES['default']['KEY_PREFIX']}:json:{specific_key}"

                serialized_data = json.dumps(response_data)
                r.setex(redis_key_json, ttl, serialized_data)
                print(f"DEBUG: Stored JSON data in Redis with key: {redis_key_json}")

                redis_result = r.get(redis_key_json)
                print(f"DEBUG: Redis verification result: {redis_result is not None}")

                logger.info(
                    f"Cached specific amount response for {ttl} seconds with key: {specific_key}"
                )
            except Exception as e:
                print(f"DEBUG: Error setting cache: {str(e)}")
                logger.exception(f"Error setting cache: {str(e)}")

            cache_corridor_rate_data(
                source_country,
                dest_country,
                source_currency,
                dest_currency,
                successful_quotes,
            )

            self._store_quotes(response_data)
        else:
            specific_key = get_quote_cache_key(
                source_country,
                dest_country,
                source_currency,
                dest_currency,
                amount_decimal,
            )
            short_ttl = min(300, settings.QUOTE_CACHE_TTL)
            cache.set(specific_key, response_data, timeout=short_ttl)
            logger.info(f"Cached failed response for {short_ttl} seconds: {specific_key}")

        return Response(response_data)

    def _sort_quotes(self, quotes, sort_by):
        """Sort quotes based on the specified criteria"""
        if not quotes or not sort_by:
            return

        if sort_by == "best_rate":
            quotes.sort(key=lambda q: (-(q.get("exchange_rate", 0) or 0)))
        elif sort_by == "lowest_fee":
            quotes.sort(key=lambda q: (q.get("fee", float("inf")) or float("inf")))
        elif sort_by == "fastest_time":
            quotes.sort(
                key=lambda q: (q.get("delivery_time_minutes", float("inf")) or float("inf"))
            )
        elif sort_by == "best_value":

            def value_score(quote):
                rate_score = quote.get("exchange_rate", 0) or 0
                fee_score = 100 - (quote.get("fee", 0) or 0) * 10
                time_score = 100 - min(100, ((quote.get("delivery_time_minutes", 0) or 0) / 30))
                return rate_score * 0.5 + fee_score * 0.3 + time_score * 0.2

            quotes.sort(key=value_score, reverse=True)

    def _log_query(
        self,
        source_country,
        dest_country,
        source_currency,
        dest_currency,
        amount,
        request,
    ):
        """Log the query for analytics (anonymously)"""
        try:
            user_ip = self._get_client_ip(request)
            QuoteQueryLog.objects.create(
                source_country=source_country,
                destination_country=dest_country,
                source_currency=source_currency,
                destination_currency=dest_currency,
                send_amount=amount,
                user_ip=user_ip,
            )
        except Exception as e:
            logger.warning(f"Failed to log query: {str(e)}")
            pass

    def _get_client_ip(self, request):
        """Extract client IP from request"""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip

    def _get_quotes_from_aggregator(
        self,
        source_country,
        dest_country,
        source_currency,
        dest_currency,
        amount,
        sort_by,
    ):
        """Get quotes from the aggregator service"""
        return Aggregator.get_all_quotes(
            source_country=source_country,
            dest_country=dest_country,
            source_currency=source_currency,
            dest_currency=dest_currency,
            amount=amount,
            sort_by=sort_by,
        )

    def _transform_response(
        self,
        raw_response,
        source_country,
        dest_country,
        source_currency,
        dest_currency,
        amount,
        sort_by,
    ):
        """Transform aggregator response to standardized format for API and caching"""
        # First create the basic response structure
        basic_response = {
            "success": raw_response.get("success", False),
            "elapsed_seconds": raw_response.get("execution_time", 0),
            "source_country": source_country,
            "dest_country": dest_country,
            "source_currency": source_currency,
            "dest_currency": dest_currency,
            "amount": float(amount),
            "quotes": raw_response.get("results", []),
            "all_providers": raw_response.get("all_results", []),
            "timestamp": timezone.now().isoformat(),
            "cache_hit": False,
            "filters_applied": {
                "sort_by": sort_by,
                "max_delivery_time_minutes": None,
                "max_fee": None,
            },
        }
        
        # Now use our transformation pipeline to clean and standardize the response
        return transform_quotes_response(basic_response)

    def _store_quotes(self, response_data):
        """Store successful quotes in the database"""
        try:
            quotes = response_data.get("quotes", [])
            stored_count = 0

            for quote in quotes:
                if not quote.get("success", False):
                    continue

                if not all(
                    [
                        quote.get("provider_id"),
                        quote.get("exchange_rate"),
                        quote.get("fee") is not None,
                        quote.get("destination_amount"),
                    ]
                ):
                    logger.warning(
                        f"Skipping quote from {quote.get('provider_id')} - missing essential data"
                    )
                    continue

                provider_id = quote.get("provider_id")
                provider, _ = Provider.objects.get_or_create(
                    id=provider_id, defaults={"name": provider_id}
                )

                payment_method = quote.get("payment_method")
                if not payment_method or payment_method == "unknown":
                    payment_method = "Card"

                delivery_method = quote.get("delivery_method")
                if not delivery_method or delivery_method == "unknown":
                    delivery_method = "bank_deposit"

                try:
                    send_amount = Decimal(str(response_data.get("amount", 0)))
                    fee_amount = Decimal(str(quote.get("fee", 0)))
                    exchange_rate = Decimal(str(quote.get("exchange_rate", 0)))
                    destination_amount = Decimal(str(quote.get("destination_amount", 0)))
                    delivery_time_minutes = int(quote.get("delivery_time_minutes", 0))
                except (ValueError, TypeError, InvalidOperation) as e:
                    logger.warning(
                        f"Skipping quote from {provider_id} - numeric conversion error: {str(e)}"
                    )
                    continue

                FeeQuote.objects.update_or_create(
                    provider=provider,
                    source_country=response_data.get("source_country"),
                    destination_country=response_data.get("dest_country"),
                    source_currency=response_data.get("source_currency"),
                    destination_currency=response_data.get("dest_currency"),
                    payment_method=payment_method,
                    delivery_method=delivery_method,
                    send_amount=send_amount,
                    defaults={
                        "fee_amount": fee_amount,
                        "exchange_rate": exchange_rate,
                        "delivery_time_minutes": delivery_time_minutes,
                        "destination_amount": destination_amount,
                        "last_updated": timezone.now(),
                    },
                )
                stored_count += 1

            logger.info(
                f"Stored {stored_count} valid quotes in database out of {len([q for q in quotes if q.get('success', False)])} successful quotes"
            )
        except Exception as e:
            logger.warning(f"Failed to store quotes: {str(e)}")
            pass
