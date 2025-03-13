"""
API views for the aggregator module.

This module defines the API views for the aggregator functionality, which combines
and compares quotes from multiple remittance providers.
"""
from decimal import Decimal, InvalidOperation

from django.conf import settings
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

from .aggregator import get_cached_aggregated_rates


@extend_schema_view(
    get=extend_schema(
        summary="Get aggregated quotes from all providers",
        description=(
            "Fetches quotes from all available remittance providers for the specified parameters. "
            "Returns a combined and sorted list of quotes with standardized response format. "
            "Results are cached for performance, with an option to force refresh."
        ),
        parameters=[
            OpenApiParameter(
                name="amount", 
                type=float, 
                location=OpenApiParameter.QUERY,
                description="The amount to send in the source currency",
                required=True,
                examples=[
                    OpenApiExample(
                        "Example Amount",
                        summary="A typical amount to send",
                        value=1000.00,
                    ),
                ]
            ),
            OpenApiParameter(
                name="from_currency", 
                type=str, 
                location=OpenApiParameter.QUERY,
                description="The source currency code (e.g., USD, EUR, GBP)",
                required=True,
                examples=[
                    OpenApiExample(
                        "US Dollar",
                        summary="US Dollar",
                        value="USD",
                    ),
                    OpenApiExample(
                        "Euro",
                        summary="Euro",
                        value="EUR",
                    ),
                ]
            ),
            OpenApiParameter(
                name="to_country", 
                type=str, 
                location=OpenApiParameter.QUERY,
                description="The destination country code (e.g., MX, IN, PH)",
                required=True,
                examples=[
                    OpenApiExample(
                        "Mexico",
                        summary="Mexico",
                        value="MX",
                    ),
                    OpenApiExample(
                        "India",
                        summary="India",
                        value="IN",
                    ),
                ]
            ),
            OpenApiParameter(
                name="force_refresh", 
                type=bool, 
                location=OpenApiParameter.QUERY,
                description="Whether to force a refresh of cached data",
                required=False,
                default=False
            ),
        ],
        responses={
            200: OpenApiResponse(
                description="Quotes retrieved successfully from all available providers",
                examples=[
                    OpenApiExample(
                        "Successful Response",
                        summary="Example of successful aggregated quotes",
                        value={
                            "timestamp": "2023-09-15T12:34:56.789Z",
                            "request": {
                                "amount": 1000.0,
                                "from_currency": "USD",
                                "to_country": "MX"
                            },
                            "cache": {
                                "ttl_seconds": 1800,
                                "ttl_hours": 0.5,
                                "force_refresh": False
                            },
                            "count": 3,
                            "results": [
                                {
                                    "provider_id": "xe",
                                    "provider_name": "XE Money Transfer",
                                    "exchange_rate": 17.85,
                                    "fee": 4.99,
                                    "amount_received": 17850.0,
                                    "amount_sent": 1000.0,
                                    "delivery_time_minutes": 60,
                                    "source_currency": "USD",
                                    "destination_currency": "MXN",
                                    "success": True
                                },
                                {
                                    "provider_id": "wise",
                                    "provider_name": "Wise",
                                    "exchange_rate": 17.82,
                                    "fee": 8.50,
                                    "amount_received": 17820.0,
                                    "amount_sent": 1000.0,
                                    "delivery_time_minutes": 180,
                                    "source_currency": "USD",
                                    "destination_currency": "MXN",
                                    "success": True
                                },
                                {
                                    "provider_id": "remitly",
                                    "provider_name": "Remitly",
                                    "exchange_rate": 17.75,
                                    "fee": 0.0,
                                    "amount_received": 17750.0,
                                    "amount_sent": 1000.0,
                                    "delivery_time_minutes": 360,
                                    "source_currency": "USD",
                                    "destination_currency": "MXN",
                                    "success": True
                                }
                            ]
                        }
                    )
                ]
            ),
            400: OpenApiResponse(
                description="Invalid parameters provided",
                examples=[
                    OpenApiExample(
                        "Missing Parameters",
                        summary="Example of missing parameters error",
                        value={
                            "error": "Please provide 'amount', 'from_currency', and 'to_country'."
                        }
                    ),
                    OpenApiExample(
                        "Invalid Amount",
                        summary="Example of invalid amount error",
                        value={
                            "error": "Invalid 'amount' provided: Amount must be positive"
                        }
                    ),
                ]
            ),
            500: OpenApiResponse(
                description="Server error"
            ),
        },
        tags=["Quotes"],
    )
)
class AggregatorRatesView(APIView):
    """
    API endpoint to get aggregated rates from all providers.
    
    This endpoint fetches quotes from all available remittance providers for the
    specified parameters and returns a combined and sorted list of quotes.
    Results are cached for performance, with an option to force refresh.
    
    This is a public endpoint - no authentication required.
    """

    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        """
        Get aggregated rates from all providers with caching

        Query Parameters:
            amount: Decimal amount to send
            from_currency: Source currency code (e.g. 'USD')
            to_country: Destination country code (e.g. 'MX')
            force_refresh: Optional boolean to force cache refresh

        Returns:
            JSON response with aggregated quotes from all providers
        """
        amount = request.query_params.get("amount")
        from_currency = request.query_params.get("from_currency")
        to_country = request.query_params.get("to_country")
        force_refresh = request.query_params.get("force_refresh", "").lower() == "true"

        # Basic validation
        if not all([amount, from_currency, to_country]):
            return Response(
                {"error": "Please provide 'amount', 'from_currency', and 'to_country'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            send_amount = Decimal(amount)
            if send_amount <= 0:
                raise ValueError("Amount must be positive")
        except (InvalidOperation, ValueError) as e:
            return Response(
                {"error": f"Invalid 'amount' provided: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Call aggregator with cache timeout from settings
        cache_timeout = getattr(settings, "CACHE_TTL", 60 * 60 * 24)  # Default 1 day
        if force_refresh:
            cache_timeout = 0  # Forces cache refresh

        results = get_cached_aggregated_rates(
            send_amount=send_amount,
            send_currency=from_currency.upper(),
            receive_country=to_country.upper(),
            cache_timeout=cache_timeout,
        )

        # Return to client with cache information
        response_data = {
            "timestamp": timezone.now().isoformat(),
            "request": {
                "amount": float(send_amount),
                "from_currency": from_currency.upper(),
                "to_country": to_country.upper(),
            },
            "cache": {
                "ttl_seconds": cache_timeout,
                "ttl_hours": round(cache_timeout / 3600, 1),
                "force_refresh": force_refresh,
            },
            "count": len(results),
            "results": results,
        }

        return Response(response_data)
