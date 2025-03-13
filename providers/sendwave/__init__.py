"""
Sendwave (Wave) Provider Package

This package implements integration with Sendwave, a digital money transfer service
that offers competitive exchange rates for international remittances.
"""

from providers.sendwave.exceptions import (
    SendwaveApiError,
    SendwaveConnectionError,
    SendwaveCorridorUnsupportedError,
    SendwaveError,
    SendwaveResponseError,
    SendwaveValidationError,
)
from providers.sendwave.integration import WaveProvider

__all__ = [
    "WaveProvider",
    "SendwaveError",
    "SendwaveConnectionError",
    "SendwaveApiError",
    "SendwaveValidationError",
    "SendwaveResponseError",
    "SendwaveCorridorUnsupportedError",
]
