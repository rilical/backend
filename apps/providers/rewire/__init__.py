"""
Rewire Money Transfer Provider package.

This package provides integration with Rewire, a cross-border money transfer
service with a focus on remittances.
"""

from apps.providers.rewire.exceptions import (
    RewireApiError,
    RewireConnectionError,
    RewireCorridorUnsupportedError,
    RewireError,
    RewireParsingError,
    RewireQuoteError,
    RewireRateLimitError,
    RewireResponseError,
    RewireValidationError,
)
from apps.providers.rewire.integration import RewireProvider

__all__ = [
    "RewireProvider",
    "RewireError",
    "RewireConnectionError",
    "RewireApiError",
    "RewireValidationError",
    "RewireRateLimitError",
    "RewireResponseError",
    "RewireCorridorUnsupportedError",
    "RewireQuoteError",
    "RewireParsingError",
]
