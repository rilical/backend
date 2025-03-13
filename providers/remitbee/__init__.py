"""
Remitbee Provider Integration

This package implements integration with Remitbee, a digital money transfer service
that offers competitive exchange rates for international remittances.

The integration accesses Remitbee's public quote API to fetch exchange rates and fees
for international money transfers.
"""

from providers.remitbee.exceptions import (
    RemitbeeApiError,
    RemitbeeConnectionError,
    RemitbeeError,
    RemitbeeRateLimitError,
    RemitbeeValidationError,
)
from providers.remitbee.integration import RemitbeeProvider

__all__ = [
    "RemitbeeProvider",
    "RemitbeeError",
    "RemitbeeConnectionError",
    "RemitbeeApiError",
    "RemitbeeValidationError",
    "RemitbeeRateLimitError",
]

__version__ = "0.1.0"
