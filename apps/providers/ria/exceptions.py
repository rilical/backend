"""RIA Money Transfer-specific exceptions."""
from typing import Any, Dict, Optional

from apps.providers.base.exceptions import ProviderError


class RIAError(ProviderError):
    """Exception raised for RIA Money Transfer-specific errors."""

    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        super().__init__(message=message, provider="RIA", error_code=error_code, details=details)


class RIAAuthenticationError(RIAError):
    """Raised when there are authentication/session issues."""

    pass


class RIAValidationError(RIAError):
    """Raised when the API rejects our input parameters."""

    pass


class RIAConnectionError(RIAError):
    """Raised when we can't connect to RIA's API."""

    pass
