"""
Custom exceptions for the TransferGo provider.
"""


class TransferGoError(Exception):
    """Base exception for all TransferGo-related errors."""

    pass


class TransferGoAuthenticationError(TransferGoError):
    """Raised when authentication with TransferGo fails."""

    pass


class TransferGoConnectionError(TransferGoError):
    """Raised when there is a connection error with TransferGo's API."""

    pass


class TransferGoValidationError(TransferGoError):
    """Raised when there are validation errors with the request."""

    pass


class TransferGoRateLimitError(TransferGoError):
    """Raised when TransferGo's rate limit is exceeded."""

    pass
