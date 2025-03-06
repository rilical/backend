"""
Exceptions specific to the XE integration.
"""

class XEError(Exception):
    """Base exception for all XE-related errors."""
    pass


class XEConnectionError(XEError):
    """Raised when there is a connection error with the XE API."""
    pass


class XEApiError(XEError):
    """Raised when the XE API returns an error."""
    pass


class XEValidationError(XEError):
    """Raised when there is a validation error with the XE API request."""
    pass


class XERateLimitError(XEError):
    """Raised when the XE API rate limit is exceeded."""
    pass


class XEResponseError(XEError):
    """Raised when there is an issue with the XE API response format."""
    pass


class XECorridorUnsupportedError(XEError):
    """Raised when attempting to use an unsupported corridor."""
    pass


class XEQuoteError(XEError):
    """Raised when there is an error retrieving a quote from XE."""
    pass


class XEParsingError(XEError):
    """Raised when there is an error parsing the XE response."""
    pass 