"""Intermex Money Transfer-specific exceptions."""
from typing import Optional, Dict, Any
from apps.providers.base.exceptions import ProviderError


class IntermexError(ProviderError):
    """Exception raised for Intermex Money Transfer-specific errors."""
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        super().__init__(
            message=message,
            provider="Intermex",
            error_code=error_code,
            details=details
        )


class IntermexAuthenticationError(IntermexError):
    """Raised when there are authentication/session issues with Intermex API."""
    pass


class IntermexValidationError(IntermexError):
    """Raised when the Intermex API rejects our input parameters."""
    pass


class IntermexConnectionError(IntermexError):
    """Raised when we can't connect to Intermex's API."""
    pass


class IntermexRateLimitError(IntermexError):
    """Raised when we exceed the API rate limits."""
    pass 