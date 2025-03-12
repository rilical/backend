"""
Pangea Money Transfer Provider Package

This package implements integration with Pangea, a remittance service provider
offering competitive exchange rates for various currency corridors.
"""

from apps.providers.pangea.exceptions import (
    PangeaAuthenticationError,
    PangeaConnectionError,
    PangeaError,
    PangeaRateLimitError,
    PangeaValidationError,
)
from apps.providers.pangea.integration import PangeaProvider

__all__ = [
    "PangeaProvider",
    "PangeaError",
    "PangeaConnectionError",
    "PangeaValidationError",
    "PangeaRateLimitError",
    "PangeaAuthenticationError",
]
