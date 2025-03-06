"""
Custom exceptions for the Placid provider.

This module defines the exception hierarchy for errors that can occur when interacting
with the Placid API.
"""

class PlacidError(Exception):
    """Base exception for all Placid related errors."""
    pass


class PlacidConnectionError(PlacidError):
    """Raised when a connection error occurs with the Placid API."""
    pass


class PlacidApiError(PlacidError):
    """Raised when the Placid API returns an error response."""
    pass


class PlacidResponseError(PlacidError):
    """Raised when there is an error parsing the Placid API response."""
    pass


class PlacidCorridorUnsupportedError(PlacidError):
    """Raised when a requested corridor is not supported by Placid."""
    pass


class PlacidCloudflareError(PlacidError):
    """Raised when there are issues with Cloudflare protection for Placid API access."""
    pass


class PlacidRateLimitError(PlacidError):
    """Raised when the API rate limit is exceeded."""
    pass 