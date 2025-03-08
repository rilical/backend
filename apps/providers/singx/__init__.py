"""
SingX provider integration package.

This package provides integration with SingX, a digital remittance service
that offers competitive exchange rates for various currency corridors.
"""

from apps.providers.singx.integration import SingXProvider, SingXAggregatorProvider
from apps.providers.singx.exceptions import (
    SingXError,
    SingXAuthError,
    SingXAPIError,
    SingXValidationError,
    SingXCorridorError,
    SingXQuoteError,
    SingXRateError
)

__all__ = [
    'SingXProvider',
    'SingXAggregatorProvider',
    'SingXError',
    'SingXAuthError',
    'SingXAPIError',
    'SingXValidationError',
    'SingXCorridorError',
    'SingXQuoteError',
    'SingXRateError'
] 