"""
RIA-specific exceptions, mirroring the Western Union pattern.
"""

from typing import Dict, Any
from apps.providers.base.exceptions import ProviderError

class RIAError(ProviderError):
    """Base exception for RIA-specific errors."""
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        super().__init__(
            message=message,
            provider="RIA",
            error_code=error_code,
            details=details
        )

class RIAAuthenticationError(RIAError):
    """Raised when there are authentication/session issues with RIA."""
    pass

class RIAValidationError(RIAError):
    """Raised when RIA's API rejects or finds invalid input."""
    pass

class RIAConnectionError(RIAError):
    """Raised when we fail to connect or receive a valid response from RIA."""
    pass 