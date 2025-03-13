from decimal import Decimal

from django.shortcuts import render
from rest_framework import status, viewsets
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from drf_spectacular.utils import (
    OpenApiExample, 
    OpenApiResponse, 
    extend_schema,
    OpenApiParameter
)
from rest_framework.permissions import AllowAny

from aggregator.aggregator import Aggregator
from .factory import ProviderFactory


class RateComparisonViewSet(viewsets.ViewSet):
    """
    A viewset for comparing remittance rates from different providers.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        summary="List all available providers",
        description="Returns a list of all available remittance providers in the system with their IDs, display names, and logo URLs (if available).",
        responses={
            200: OpenApiResponse(
                description="List of available providers",
                examples=[
                    OpenApiExample(
                        "Providers List",
                        summary="Example list of available providers",
                        value={
                            "providers": [
                                {
                                    "id": "XE",
                                    "name": "XE Money Transfer",
                                    "logo_url": "https://example.com/xe-logo.png"
                                },
                                {
                                    "id": "WISE",
                                    "name": "Wise",
                                    "logo_url": "https://example.com/wise-logo.png"
                                },
                                {
                                    "id": "REMITLY",
                                    "name": "Remitly",
                                    "logo_url": "https://example.com/remitly-logo.png"
                                }
                            ],
                            "count": 3
                        }
                    )
                ]
            )
        },
        tags=["Providers"]
    )
    @action(detail=False, methods=["get"], url_path="list")
    def list_providers(self, request):
        """
        Get a list of all available remittance providers.
        
        This endpoint returns a comprehensive list of all remittance providers 
        integrated with the RemitScout system. For each provider, it includes:
        - id: The unique identifier used in API calls
        - name: The human-readable display name
        - logo_url: URL to the provider's logo image (if available)
        
        Returns:
            Response: A JSON object containing:
                - providers: List of provider objects with their details
                - count: Total number of available providers
        """
        provider_names = ProviderFactory.list_providers()
        providers = []
        
        for name in provider_names:
            try:
                # Create a temporary instance to get the display name
                provider = ProviderFactory.get_provider(name)
                provider_data = {
                    "id": provider.get_provider_id().upper(),
                    "name": provider.get_display_name(),
                }
                
                # Add logo URL if available (would come from a Provider model in a real implementation)
                # This is a placeholder - in a real implementation, you would fetch this from a database
                # or configuration
                logo_url = None
                try:
                    # Try to get from Provider model if it exists
                    from quotes.models import Provider as ProviderModel
                    provider_model = ProviderModel.objects.filter(id=provider.get_provider_id().upper()).first()
                    if provider_model and provider_model.logo_url:
                        logo_url = provider_model.logo_url
                except (ImportError, Exception):
                    # If Provider model doesn't exist or there's an error, use a default pattern
                    logo_url = f"https://remitscout.com/logos/{provider.get_provider_id().upper()}.png"
                
                if logo_url:
                    provider_data["logo_url"] = logo_url
                    
                providers.append(provider_data)
            except Exception as e:
                # Skip providers that can't be instantiated
                continue
        
        return Response({
            "providers": providers,
            "count": len(providers)
        })

    @extend_schema(
        summary="Get provider details",
        description="Returns basic information about a specific remittance provider",
        parameters=[
            OpenApiParameter(
                name="provider_id", 
                type=str, 
                location=OpenApiParameter.PATH,
                description="The unique identifier of the provider",
                required=True,
                examples=[
                    OpenApiExample("XE Money Transfer", value="XE"),
                    OpenApiExample("Wise", value="WISE"),
                ]
            ),
        ],
        responses={
            200: OpenApiResponse(
                description="Provider details retrieved successfully",
                examples=[
                    OpenApiExample(
                        "Provider Details",
                        summary="Example provider details",
                        value={
                            "id": "XE",
                            "name": "XE Money Transfer",
                            "logo_url": "https://remitscout.com/logos/XE.png",
                            "website": "https://www.xe.com/send-money/",
                            "transfer_types": ["international"],
                            "supported_payment_methods": ["bank_transfer", "debit_card", "credit_card"],
                            "supported_delivery_methods": ["bank_deposit"]
                        }
                    )
                ]
            ),
            404: OpenApiResponse(
                description="Provider not found",
                examples=[
                    OpenApiExample(
                        "Provider Not Found",
                        summary="Example of provider not found error",
                        value={
                            "error": "Provider 'invalid_provider' not found"
                        }
                    )
                ]
            )
        },
        tags=["Providers"]
    )
    @action(detail=True, methods=["get"], url_path="details")
    def provider_details(self, request, pk=None):
        """
        Get basic information about a specific remittance provider.
        
        This endpoint returns essential details about a specific provider, including:
        - Basic information (ID, name, logo URL)
        - Website URL (if available)
        - Transfer types (international, domestic)
        - Supported payment and delivery methods
        
        Args:
            request: The HTTP request
            pk: The provider ID
            
        Returns:
            Response: A JSON object containing the provider details
        """
        try:
            # Convert pk to uppercase to ensure case-insensitive lookup
            pk_upper = pk.upper() if pk else None
            
            # Get the provider instance
            provider = ProviderFactory.get_provider(pk_upper)
            
            # Build the response with basic provider information
            response_data = {
                "id": provider.get_provider_id().upper(),
                "name": provider.get_display_name(),
            }
            
            # Add logo URL if available
            try:
                from quotes.models import Provider as ProviderModel
                provider_model = ProviderModel.objects.filter(id=provider.get_provider_id().upper()).first()
                if provider_model:
                    if provider_model.logo_url:
                        response_data["logo_url"] = provider_model.logo_url
                    if provider_model.website:
                        response_data["website"] = provider_model.website
            except (ImportError, Exception):
                # If Provider model doesn't exist or there's an error, use a default pattern for logo
                response_data["logo_url"] = f"https://remitscout.com/logos/{provider.get_provider_id().upper()}.png"
                
                # For website, use a pattern based on the provider ID
                website_map = {
                    "XE": "https://www.xe.com/send-money/",
                    "WISE": "https://wise.com/",
                    "REMITLY": "https://www.remitly.com/",
                    "RIA": "https://www.riamoneytransfer.com/",
                    "TRANSFERGO": "https://www.transfergo.com/",
                    "WESTERNUNION": "https://www.westernunion.com/",
                    "XOOM": "https://www.xoom.com/",
                    "SINGX": "https://www.singx.co/",
                    "PAYSEND": "https://paysend.com/",
                    "ALANSARI": "https://www.alansariexchange.com/",
                    "REMITBEE": "https://www.remitbee.com/",
                    "INSTAREM": "https://www.instarem.com/",
                    "PANGEA": "https://www.pangea.com/",
                    "KORONAPAY": "https://koronapay.com/",
                    "MUKURU": "https://www.mukuru.com/",
                    "REWIRE": "https://www.rewire.to/",
                    "SENDWAVE": "https://www.sendwave.com/",
                    "WIREBARLEY": "https://www.wirebarley.com/",
                    "ORBITREMIT": "https://www.orbitremit.com/",
                    "DAHABSHIIL": "https://www.dahabshiil.com/",
                    "INTERMEX": "https://www.intermexonline.com/",
                    "PLACID": "https://placid.app/",
                    "REMITGURU": "https://www.remitguru.com/"
                }
                
                if provider.get_provider_id().upper() in website_map:
                    response_data["website"] = website_map[provider.get_provider_id().upper()]
            
            # Add supported methods - simplified defaults
            # This is just a basic schema - real data would come from the database or provider configuration
            response_data["transfer_types"] = ["international"]
            
            # Use standard methods as defaults
            response_data["supported_payment_methods"] = ["bank_transfer", "debit_card", "credit_card"]
            response_data["supported_delivery_methods"] = ["bank_deposit"]
            
            return Response(response_data)
        except ValueError:
            return Response(
                {"error": f"Provider '{pk}' not found"},
                status=status.HTTP_404_NOT_FOUND
            )


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


@require_http_methods(["GET"])
def send_money_view(request):
    """Placeholder for send money view"""
    return JsonResponse({"message": "Send money functionality coming soon"})
