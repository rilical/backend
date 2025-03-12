"""
SingX provider integration package.

This package provides integration with SingX, a digital remittance service
that offers competitive exchange rates for various currency corridors.
"""

from apps.providers.singx.exceptions import (
    SingXAPIError,
    SingXAuthError,
    SingXCorridorError,
    SingXError,
    SingXQuoteError,
    SingXRateError,
    SingXValidationError,
)
from apps.providers.singx.integration import SingXAggregatorProvider, SingXProvider

__all__ = [
    "SingXProvider",
    "SingXAggregatorProvider",
    "SingXError",
    "SingXAuthError",
    "SingXAPIError",
    "SingXValidationError",
    "SingXCorridorError",
    "SingXQuoteError",
    "SingXRateError",
]
