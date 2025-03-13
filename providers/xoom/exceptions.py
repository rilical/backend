"""Xoom-specific exceptions."""
from typing import Any, Dict, Optional

from providers.base.exceptions import ProviderError


class XoomError(ProviderError):
    """Exception raised for Xoom-specific errors."""

    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        super().__init__(message=message, provider="Xoom", error_code=error_code, details=details)


class XoomAuthenticationError(XoomError):
    """Raised when there are authentication/session issues with Xoom API."""

    pass


class XoomValidationError(XoomError):
    """Raised when the Xoom API rejects our input parameters."""

    pass


class XoomConnectionError(XoomError):
    """Raised when we can't connect to Xoom's API."""

    pass


class XoomRateLimitError(XoomError):
    """Raised when we exceed the API rate limits."""

    pass
