"""
Custom exceptions for the Dahabshiil provider.
"""

class DahabshiilError(Exception):
    """Base exception for all Dahabshiil-related errors."""
    pass


class DahabshiilConnectionError(DahabshiilError):
    """Raised when there's an issue connecting to the Dahabshiil API."""
    pass


class DahabshiilApiError(DahabshiilError):
    """Raised when the Dahabshiil API returns an error response."""
    pass


class DahabshiilResponseError(DahabshiilError):
    """Raised when there's an issue parsing the Dahabshiil API response."""
    pass


class DahabshiilCorridorUnsupportedError(DahabshiilError):
    """Raised when a requested corridor is not supported by Dahabshiil."""
    pass


class DahabshiilRateLimitError(DahabshiilError):
    """Raised when we exceed the rate limit for Dahabshiil API calls."""
    pass 