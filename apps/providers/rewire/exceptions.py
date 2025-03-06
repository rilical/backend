"""
Exceptions specific to the Rewire integration.
"""

class RewireError(Exception):
    """Base exception for all Rewire-related errors."""
    pass


class RewireConnectionError(RewireError):
    """Raised when there is a connection error with the Rewire API."""
    pass


class RewireApiError(RewireError):
    """Raised when the Rewire API returns an error."""
    pass


class RewireValidationError(RewireError):
    """Raised when there is a validation error with the Rewire API request."""
    pass


class RewireRateLimitError(RewireError):
    """Raised when the Rewire API rate limit is exceeded."""
    pass


class RewireResponseError(RewireError):
    """Raised when there is an issue with the Rewire API response format."""
    pass


class RewireCorridorUnsupportedError(RewireError):
    """Raised when attempting to use an unsupported corridor."""
    pass


class RewireQuoteError(RewireError):
    """Raised when there is an error retrieving a quote from Rewire."""
    pass


class RewireParsingError(RewireError):
    """Raised when there is an error parsing the Rewire response."""
    pass 