"""
TransferGo provider package.

This package provides integration with TransferGo, a digital remittance service
with competitive rates for international money transfers.
"""

# Import the standard provider
from apps.providers.transfergo.integration import TransferGoProvider as StandardTransferGoProvider

# Import the aggregator-specific provider
from apps.providers.transfergo.aggregator_integration import TransferGoProvider as AggregatorTransferGoProvider

# Import exceptions
from apps.providers.transfergo.exceptions import (
    TransferGoError,
    TransferGoAuthenticationError,
    TransferGoConnectionError,
    TransferGoValidationError,
    TransferGoRateLimitError
)

# Export both providers with clear names
TransferGoProvider = StandardTransferGoProvider
TransferGoAggregatorProvider = AggregatorTransferGoProvider

__all__ = [
    'TransferGoProvider',
    'TransferGoAggregatorProvider',
    'TransferGoError',
    'TransferGoAuthenticationError',
    'TransferGoConnectionError',
    'TransferGoValidationError',
    'TransferGoRateLimitError'
] 