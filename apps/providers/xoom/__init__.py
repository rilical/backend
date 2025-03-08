"""Xoom integration package."""
from apps.providers.xoom.integration import XoomProvider

# If there's an aggregator-specific provider, include it
try:
    from apps.providers.xoom.aggregator import XoomAggregatorProvider
    __all__ = ["XoomProvider", "XoomAggregatorProvider"]
except ImportError:
    __all__ = ["XoomProvider"] 