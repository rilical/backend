"""
Placid provider integration module.

This module provides integration with Placid (https://www.placid.net/),
a remittance service that offers competitive exchange rates for various 
currency corridors.

Example usage:
    from apps.providers import get_provider_by_name
    
    # Get the provider instance
    provider = get_provider_by_name("placid")
    
    # Get exchange rate
    result = provider.get_exchange_rate(
        source_country="US",
        corridor_val="PAK",
        rndval="1740963881748"
    )
    
    # Check result
    if result["success"]:
        print(f"Exchange rate: {result['rate']}")
    else:
        print(f"Error: {result['error_message']}")
"""

from .exceptions import (
    PlacidApiError,
    PlacidCloudflareError,
    PlacidConnectionError,
    PlacidCorridorUnsupportedError,
    PlacidError,
    PlacidRateLimitError,
    PlacidResponseError,
)
from .integration import PlacidProvider

__all__ = [
    "PlacidProvider",
    "PlacidError",
    "PlacidConnectionError",
    "PlacidApiError",
    "PlacidResponseError",
    "PlacidCorridorUnsupportedError",
    "PlacidCloudflareError",
    "PlacidRateLimitError",
]
