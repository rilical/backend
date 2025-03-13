"""Xoom integration package."""
from providers.xoom.integration import XoomProvider

# If there's an aggregator-specific provider, include it
try:
    from providers.xoom.aggregator import XoomAggregatorProvider

    __all__ = ["XoomProvider", "XoomAggregatorProvider"]
except ImportError:
    __all__ = ["XoomProvider"]
