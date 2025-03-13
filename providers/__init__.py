"""
Remittance providers package.

This package contains implementations for various remittance providers
that can be used to get exchange rates and fees.
"""

from .factory import ProviderFactory
from decimal import Decimal
from typing import Dict, Any, List, Optional


# Expose helpful functions
def get_provider_by_name(provider_name, **kwargs):
    """
    Get a provider instance by name.

    Args:
        provider_name: Name of the provider
        **kwargs: Additional arguments to pass to the provider

    Returns:
        An instance of the requested provider
    """
    return ProviderFactory.get_provider(provider_name, **kwargs)


def get_quote(
    amount: Decimal,
    source_currency: str,
    dest_currency: str,
    source_country: str,
    dest_country: str,
    provider_name: Optional[str] = None,
    payment_method: Optional[str] = None,
    delivery_method: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Get a quote from a specific provider or all providers.
    
    Args:
        amount: Amount to transfer
        source_currency: Source currency code
        dest_currency: Destination currency code
        source_country: Source country code
        dest_country: Destination country code
        provider_name: Name of the provider (if None, returns quotes from all providers)
        payment_method: Payment method (default: None)
        delivery_method: Delivery method (default: None)
        **kwargs: Additional parameters to pass to the provider
        
    Returns:
        If provider_name is specified: A quote from that provider
        If provider_name is None: A dict with quotes from all providers
    """
    # If a specific provider is requested, return just that quote
    if provider_name:
        provider = get_provider_by_name(provider_name)
        return provider.get_quote(
            amount=amount,
            source_currency=source_currency,
            dest_currency=dest_currency,
            source_country=source_country,
            dest_country=dest_country,
            payment_method=payment_method,
            delivery_method=delivery_method,
            **kwargs
        )
    
    # If no provider specified, return quotes from all providers
    from aggregator.aggregator import Aggregator
    return Aggregator.get_all_quotes(
        amount=amount,
        source_currency=source_currency,
        dest_currency=dest_currency,
        source_country=source_country,
        dest_country=dest_country,
    )


def list_providers():
    """
    Get a list of all registered provider names.

    Returns:
        List of provider names
    """
    return ProviderFactory.list_providers()
