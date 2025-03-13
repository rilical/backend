"""
Exception classes for the Pangea Money Transfer API integration.
"""


class PangeaError(Exception):
    """Base exception class for Pangea-related errors."""

    def __init__(self, message: str, error_code: str = None, details: dict = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self):
        if self.error_code:
            return f"{self.message} (Error code: {self.error_code})"
        return self.message


class PangeaConnectionError(PangeaError):
    """Raised when there's an issue connecting to the Pangea API."""

    pass


class PangeaValidationError(PangeaError):
    """Raised when the API request has invalid parameters."""

    pass


class PangeaRateLimitError(PangeaError):
    """Raised when the API rate limit is exceeded."""

    pass


class PangeaAuthenticationError(PangeaError):
    """Raised when there's an authentication issue with the API."""

    pass
