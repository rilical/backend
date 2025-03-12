from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .aggregator import get_cached_aggregated_rates


class AggregatorRatesView(APIView):
    """
    Single endpoint to get aggregated rates from all providers
    """

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
