"""
Mukuru-specific exceptions.

This module defines custom exceptions that may be raised
during interactions with the Mukuru remittance provider.
"""

class MukuruError(Exception):
    """Base exception for all Mukuru-related errors."""
    pass

class MukuruConnectionError(MukuruError):
    """Raised when there's an error connecting to the Mukuru API."""
    pass

class MukuruApiError(MukuruError):
    """Raised when the Mukuru API returns an error response."""
    pass

class MukuruResponseError(MukuruError):
    """Raised when there's an error parsing the Mukuru API response."""
    pass

class MukuruCorridorUnsupportedError(MukuruError):
    """Raised when a requested corridor (source -> destination) is not supported."""
    pass

class MukuruRateLimitError(MukuruError):
    """Raised when the API rate limit is exceeded."""
    pass 