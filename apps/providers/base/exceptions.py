"""Provider-specific exceptions module."""
from typing import Optional, Dict, Any


class ProviderError(Exception):
    """Base class for all provider-related errors."""

    def __init__(
        self,
        message: str,
        provider: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.provider = provider
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)
