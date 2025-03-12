"""
Celery tasks for updating provider rates.
"""
from decimal import Decimal

from celery import shared_task
from django.utils import timezone

from .factory import ProviderFactory
from .models import ExchangeRate, Provider


@shared_task
def update_provider_rates(
    provider_name: str, send_amount: float, send_currency: str, receive_country: str
) -> str:
    """
    Update rates for a specific provider.

    Args:
        provider_name: Name of the provider (e.g., 'western_union')
        send_amount: Amount to send
        send_currency: Currency code to send (e.g., 'USD')
        receive_country: Destination country code (e.g., 'MX')
    """
    try:
        # Get provider instance from factory
        provider_instance = ProviderFactory.get_provider(provider_name, headless=True)

        with provider_instance as provider:
            # Get current rates
            rate_info = provider.get_exchange_rate(
                send_amount=Decimal(str(send_amount)),
                send_currency=send_currency,
                receive_country=receive_country,
            )

            if rate_info:
                # Get or create provider record
                provider_obj, _ = Provider.objects.get_or_create(
                    name=rate_info["provider"],
                    defaults={"website": provider_instance.base_url},
                )

                # Create new rate record
                ExchangeRate.objects.create(
                    provider=provider_obj,
                    send_amount=Decimal(str(rate_info["send_amount"])),
                    send_currency=rate_info["send_currency"],
                    receive_country=rate_info["receive_country"],
                    exchange_rate=Decimal(str(rate_info["exchange_rate"])),
                    transfer_fee=Decimal(str(rate_info["transfer_fee"])),
                    delivery_time=rate_info["delivery_time"],
                    timestamp=timezone.now(),
                )

                return f"Updated rates for {provider_name}"

            return f"No rates available for {provider_name}"

    except Exception as e:
        return f"Error updating {provider_name} rates: {str(e)}"


@shared_task
def update_all_rates(send_amount: float, send_currency: str, receive_country: str) -> dict:
    """
    Update rates for all available providers.

    Args:
        send_amount: Amount to send
        send_currency: Currency code to send (e.g., 'USD')
        receive_country: Destination country code (e.g., 'MX')
    """
    results = {}

    # Get list of all available providers
    providers = ProviderFactory.list_providers()

    # Update rates for each provider
    for provider_name in providers:
        task = update_provider_rates.delay(
            provider_name, send_amount, send_currency, receive_country
        )
        results[provider_name] = task.id

    return results
