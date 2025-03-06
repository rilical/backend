"""
API views for comparing remittance provider rates.
"""
from datetime import timedelta
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters import rest_framework as filters
from django.shortcuts import render
from django.contrib import messages
from decimal import Decimal

from .models import Provider, ExchangeRate
from .serializers import ProviderSerializer, ExchangeRateSerializer
from .tasks import update_all_rates
from .forms import SendMoneyForm
from .westernunion.integration import WesternUnionProvider
from .westernunion.exceptions import (
    WUError,
    WUAuthenticationError,
    WUValidationError,
    WUConnectionError
)
from .worldremit.integration import WorldRemitProvider
from .worldremit.exceptions import (
    WorldRemitError,
    WorldRemitAuthenticationError,
    WorldRemitValidationError,
    WorldRemitConnectionError
)

class ExchangeRateFilter(filters.FilterSet):
    """Filter set for exchange rates."""

    min_amount = filters.NumberFilter(field_name='send_amount', lookup_expr='gte')
    max_amount = filters.NumberFilter(field_name='send_amount', lookup_expr='lte')
    from_currency = filters.CharFilter(field_name='send_currency')
    to_country = filters.CharFilter(field_name='receive_country')
    provider = filters.CharFilter(field_name='provider__name')

    class Meta:
        model = ExchangeRate
        fields = ['send_currency', 'receive_country', 'provider']

class RateComparisonViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for comparing remittance provider rates.
    """
    serializer_class = ExchangeRateSerializer
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = ExchangeRateFilter

    def get_queryset(self):
        """Get the latest rates within the last hour."""
        one_hour_ago = timezone.now() - timedelta(hours=1)
        return ExchangeRate.objects.select_related('provider').filter(
            timestamp__gte=one_hour_ago,
            is_available=True
        )

    @action(detail=False, methods=['get'])
    def compare(self, request):
        """
        Compare rates across providers for a specific amount and currency pair.

        Query Parameters:
            amount: Amount to send (e.g., 1000)
            from_currency: Send currency code (e.g., 'USD')
            to_country: Receive country code (e.g., 'MX')
        """
        amount = request.query_params.get('amount')
        from_currency = request.query_params.get('from_currency')
        to_country = request.query_params.get('to_country')

        if not all([amount, from_currency, to_country]):
            return Response({
                'error': 'Please provide amount, from_currency, and to_country parameters'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            amount = float(amount)
        except ValueError:
            return Response({
                'error': 'Invalid amount'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Build cache key
        cache_key = f"rates_{amount}_{from_currency.upper()}_{to_country.upper()}"
        cached_response = cache.get(cache_key)
        if cached_response:
            return Response(cached_response)

        # Get the latest rate for each provider
        one_hour_ago = timezone.now() - timedelta(hours=1)
        rates = ExchangeRate.objects.filter(
            send_amount=amount,
            send_currency=from_currency.upper(),
            receive_country=to_country.upper(),
            timestamp__gte=one_hour_ago,
            is_available=True
        ).select_related('provider')

        if not rates.exists():
            # Trigger rate update if no recent rates found
            update_all_rates.delay(
                send_amount=amount,
                send_currency=from_currency.upper(),
                receive_country=to_country.upper()
            )
            return Response({
                'message': 'Rates are being updated. Please try again in a few moments.'
            }, status=status.HTTP_202_ACCEPTED)

        serializer = self.get_serializer(rates, many=True)
        response_data = {
            'rates': serializer.data,
            'timestamp': timezone.now().isoformat()
        }

        # Cache the response for CACHE_TTL seconds (default 10 minutes)
        cache.set(cache_key, response_data, timeout=getattr(settings, 'CACHE_TTL', 600))

        return Response(response_data)

def send_money_view(request):
    """
    View to handle the money transfer form and get Western Union quotes.
    """
    if request.method == 'POST':
        form = SendMoneyForm(request.POST)
        if form.is_valid():
            # Extract cleaned data
            cd = form.cleaned_data
            send_amount = cd['send_amount']
            send_currency = cd['send_currency']
            receive_country = cd['receive_country']
            send_country = cd['send_country']

            # Optional location data
            postal_code = cd.get('sender_postal_code')
            city = cd.get('sender_city')
            state = cd.get('sender_state')

            # Initialize WU provider
            wu = WesternUnionProvider(timeout=30)

            try:
                # Get exchange rate quote
                rate_data = wu.get_exchange_rate(
                    send_amount,
                    send_currency,
                    receive_country,
                    send_country
                )

                if rate_data is None:
                    messages.error(
                        request,
                        "Unable to get a valid quote. Please try again or choose different options."
                    )
                    return render(request, 'providers/send_money_form.html', {'form': form})

                # Store successful quote in session for next step
                request.session['wu_quote'] = rate_data
                
                # Show success template with quote details
                return render(request, 'providers/send_money_quote.html', {
                    'rate_data': rate_data,
                    'form_data': cd
                })

            except WUValidationError as e:
                messages.error(request, f"Invalid input: {str(e)}")
            except WUAuthenticationError as e:
                messages.error(request, "Authentication error with Western Union. Please try again.")
            except WUConnectionError as e:
                messages.error(request, "Connection error with Western Union. Please try again later.")
            except WUError as e:
                messages.error(request, f"Western Union error: {str(e)}")
            except Exception as e:
                messages.error(request, "An unexpected error occurred. Please try again later.")
                
            return render(request, 'providers/send_money_form.html', {'form': form})
    else:
        # GET request - show empty form
        form = SendMoneyForm()
    
    return render(request, 'providers/send_money_form.html', {'form': form})
