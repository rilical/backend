from decimal import Decimal

from django.shortcuts import render
from rest_framework import status, viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.aggregator.aggregator import Aggregator


class RateComparisonViewSet(viewsets.ViewSet):
    """
    A viewset for comparing remittance rates from different providers.
    """

    def list(self, request):
        """
        List all available providers and their rates
        """
        # Extract parameters
        source_country = request.query_params.get("source_country")
        dest_country = request.query_params.get("dest_country")
        source_currency = request.query_params.get("source_currency")
        dest_currency = request.query_params.get("dest_currency")
        amount_str = request.query_params.get("amount")

        # Validate parameters
        if not all([source_country, dest_country, source_currency, dest_currency, amount_str]):
            return Response(
                {
                    "error": "Missing required parameters. Please provide source_country, dest_country, source_currency, dest_currency, and amount."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            amount = Decimal(amount_str)
        except (ValueError, TypeError):
            return Response(
                {"error": "Invalid amount. Please provide a valid decimal number."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get rates
        rates = Aggregator.get_all_quotes(
            source_country=source_country,
            dest_country=dest_country,
            source_currency=source_currency,
            dest_currency=dest_currency,
            amount=amount,
        )

        return Response(rates)


@api_view(["GET"])
def provider_list(request):
    """
    List all available providers
    """
    providers = Aggregator.get_available_providers()
    return Response({"providers": providers})


@api_view(["GET"])
def corridor_list(request):
    """
    List all available corridors (source/destination country pairs)
    """
    corridors = Aggregator.get_available_corridors()
    return Response({"corridors": corridors})


@api_view(["GET"])
def currency_list(request):
    """
    List all available currencies
    """
    currencies = Aggregator.get_available_currencies()
    return Response({"currencies": currencies})


@api_view(["POST"])
def send_money_view(request):
    """
    Process a send money request
    """
    # This would typically handle the actual money transfer
    # but for now we'll just return a placeholder response
    return Response(
        {
            "message": "Money transfer initiated",
            "transaction_id": "mock-txn-12345",
            "status": "pending",
        }
    )
