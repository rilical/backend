"""
Views for the aggregator API.
"""
from decimal import Decimal

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from aggregator.aggregator import Aggregator


class AggregatorRatesView(APIView):
    """
    API endpoint that allows querying the aggregator for remittance rates.
    """

    def get(self, request, format=None):
        """
        Get remittance rates from the aggregator service.
        """
        # Extract parameters from query string
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

        # Query the aggregator
        try:
            results = Aggregator.get_all_quotes(
                source_country=source_country,
                dest_country=dest_country,
                source_currency=source_currency,
                dest_currency=dest_currency,
                amount=amount,
            )
            return Response(results)
        except Exception as e:
            return Response(
                {"error": f"Failed to get rates: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
