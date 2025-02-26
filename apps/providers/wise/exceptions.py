"""Wise (TransferWise)-specific exceptions."""
from typing import Optional, Dict, Any
from apps.providers.base.exceptions import ProviderError


class WiseError(ProviderError):
    """Exception raised for Wise-specific errors."""
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        super().__init__(
            message=message,
            provider="Wise",
            error_code=error_code,
            details=details
        )


class WiseAuthenticationError(WiseError):
    """Raised when there are authentication/session issues with Wise API."""
    pass


class WiseValidationError(WiseError):
    """Raised when the Wise API rejects our input parameters."""
    pass


class WiseConnectionError(WiseError):
    """Raised when we can't connect to Wise's API."""
    pass


class WiseRateLimitError(WiseError):
    """Raised when we exceed the API rate limits."""
    pass 