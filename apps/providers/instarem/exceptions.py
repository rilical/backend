"""
Custom exceptions for the InstaRem provider.
"""


class InstaRemError(Exception):
    """Base exception for all InstaRem-related errors."""

    pass


class InstaRemAuthenticationError(InstaRemError):
    """Error related to authentication with InstaRem API."""

    pass


class InstaRemConnectionError(InstaRemError):
    """Error connecting to InstaRem API."""

    pass


class InstaRemValidationError(InstaRemError):
    """Error validating input parameters for InstaRem requests."""

    pass


class InstaRemRateLimitError(InstaRemError):
    """Error when rate limits are exceeded for InstaRem API."""

    pass


class InstaRemApiError(InstaRemError):
    """Error when the InstaRem API returns an error response."""

    pass
