"""
Exceptions specific to the Sendwave integration.
"""


class SendwaveError(Exception):
    """Base exception for all Sendwave-related errors."""

    pass


class SendwaveConnectionError(SendwaveError):
    """Raised when there is a connection error with the Sendwave API."""

    pass


class SendwaveApiError(SendwaveError):
    """Raised when the Sendwave API returns an error."""

    pass


class SendwaveValidationError(SendwaveError):
    """Raised when there is a validation error with the Sendwave API request."""

    pass


class SendwaveRateLimitError(SendwaveError):
    """Raised when the Sendwave API rate limit is exceeded."""

    pass


class SendwaveResponseError(SendwaveError):
    """Raised when there is an issue with the Sendwave API response format."""

    pass


class SendwaveCorridorUnsupportedError(SendwaveError):
    """Raised when attempting to use an unsupported corridor."""

    pass
