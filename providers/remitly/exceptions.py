"""
Exceptions specific to the Remitly integration.
"""


class RemitlyError(Exception):
    """Base exception for all Remitly-related errors."""

    pass


class RemitlyAuthenticationError(RemitlyError):
    """Raised when there is an authentication failure with the Remitly API."""

    pass


class RemitlyConnectionError(RemitlyError):
    """Raised when there is a connection error with the Remitly API."""

    pass


class RemitlyValidationError(RemitlyError):
    """Raised when there is a validation error with the Remitly API request."""

    pass


class RemitlyRateLimitError(RemitlyError):
    """Raised when the Remitly API rate limit is exceeded."""

    pass
