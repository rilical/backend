"""
Mukuru integration module.

This module provides integration with the Mukuru money transfer service,
which focuses on remittances from South Africa to various African countries
and beyond.

Example usage:
    from providers.factory import ProviderFactory

    provider = ProviderFactory.get_provider('mukuru')
    rate_info = provider.get_exchange_rate(
        send_amount=Decimal('900'),
        send_currency='ZAR',
        receive_country='ZW'
    )
    print(rate_info)
"""

from .exceptions import (
    MukuruApiError,
    MukuruConnectionError,
    MukuruCorridorUnsupportedError,
    MukuruError,
    MukuruRateLimitError,
    MukuruResponseError,
)
from .integration import MukuruProvider

__all__ = [
    "MukuruProvider",
    "MukuruError",
    "MukuruConnectionError",
    "MukuruApiError",
    "MukuruResponseError",
    "MukuruCorridorUnsupportedError",
    "MukuruRateLimitError",
]
