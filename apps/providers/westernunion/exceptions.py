"""Western Union-specific exceptions."""
from typing import Any, Dict, Optional

from apps.providers.base.exceptions import ProviderError


class WUError(ProviderError):
    """Exception raised for WesternUnion-specific errors."""

    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        super().__init__(
            message=message,
            provider="Western Union",
            error_code=error_code,
            details=details,
        )


class WUAuthenticationError(WUError):
    """Raised when there are authentication/session issues."""

    pass


class WUValidationError(WUError):
    """Raised when the API rejects our input parameters."""

    pass


class WUConnectionError(WUError):
    """Raised when we can't connect to WU's API."""

    pass
