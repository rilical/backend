"""
OrbitRemit provider integration module.

This module provides integration with OrbitRemit's API for retrieving remittance
fee information between various currency pairs, particularly for transfers from
countries like Australia to destinations in Asia and Pacific regions.

Example usage:
    from providers.orbitremit import OrbitRemitProvider

    provider = OrbitRemitProvider()
    result = provider.get_fee_info(
        send_currency="AUD",
        payout_currency="PHP",
        send_amount=Decimal("200000"),
        recipient_type="bank_account"
    )
    print(f"Fee: {result['fee']}")
"""

from .exceptions import (
    OrbitRemitApiError,
    OrbitRemitConnectionError,
    OrbitRemitCorridorUnsupportedError,
    OrbitRemitError,
    OrbitRemitResponseError,
)
from .integration import OrbitRemitProvider

__all__ = [
    "OrbitRemitProvider",
    "OrbitRemitError",
    "OrbitRemitConnectionError",
    "OrbitRemitApiError",
    "OrbitRemitResponseError",
    "OrbitRemitCorridorUnsupportedError",
]
