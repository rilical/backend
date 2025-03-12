"""
Dahabshiil integration module.

This module provides integration with the Dahabshiil money transfer service,
which offers international remittance services with a strong presence in
East Africa and the Middle East.

Example usage:
    from apps.providers.factory import ProviderFactory

    provider = ProviderFactory.get_provider('dahabshiil')
    rate_info = provider.get_exchange_rate(
        send_amount=Decimal('700.00'),
        send_currency='USD',
        source_country_code='US',
        receive_country_code='KE',
        receive_currency='USD',
        payout_type='Cash Collection'
    )
    print(rate_info)
"""

from .exceptions import (
    DahabshiilApiError,
    DahabshiilConnectionError,
    DahabshiilCorridorUnsupportedError,
    DahabshiilError,
    DahabshiilRateLimitError,
    DahabshiilResponseError,
)
from .integration import DahabshiilProvider

__all__ = [
    "DahabshiilProvider",
    "DahabshiilError",
    "DahabshiilConnectionError",
    "DahabshiilApiError",
    "DahabshiilResponseError",
    "DahabshiilCorridorUnsupportedError",
    "DahabshiilRateLimitError",
]
