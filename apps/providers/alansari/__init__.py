"""
Al Ansari Exchange integration module.

This module provides integration with Al Ansari Exchange, a leading remittance service
based in the UAE with a strong presence in the Middle East and South Asia.

Example usage:
    from apps.providers.factory import ProviderFactory

    provider = ProviderFactory.get_provider('alansari')
    rate_info = provider.get_exchange_rate(
        send_amount=Decimal('1.00'),
        from_currency_id='91',  # AED
        to_currency_id='27',    # INR
        security_token='50fd6ea0d6',
        transfer_type='BT'
    )
    print(rate_info)
"""

from .exceptions import (
    AlAnsariApiError,
    AlAnsariConnectionError,
    AlAnsariCorridorUnsupportedError,
    AlAnsariError,
    AlAnsariRateLimitError,
    AlAnsariResponseError,
    AlAnsariSecurityTokenError,
)
from .integration import AlAnsariProvider

__all__ = [
    "AlAnsariProvider",
    "AlAnsariError",
    "AlAnsariConnectionError",
    "AlAnsariApiError",
    "AlAnsariResponseError",
    "AlAnsariCorridorUnsupportedError",
    "AlAnsariRateLimitError",
    "AlAnsariSecurityTokenError",
]
