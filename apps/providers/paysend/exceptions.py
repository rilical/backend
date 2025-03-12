"""
Custom exceptions for the Paysend provider.
"""
from typing import Any, Dict, Optional

from apps.providers.base.exceptions import ProviderError


class PaysendError(ProviderError):
    """Base exception for all Paysend-related errors."""

    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        super().__init__(
            message=message, provider="Paysend", error_code=error_code, details=details
        )


class PaysendAuthenticationError(PaysendError):
    """Error related to authentication with Paysend API."""

    pass


class PaysendConnectionError(PaysendError):
    """Error connecting to Paysend API."""

    pass


class PaysendValidationError(PaysendError):
    """Error validating input parameters for Paysend requests."""

    pass


class PaysendRateLimitError(PaysendError):
    """Error when rate limits are exceeded for Paysend API."""

    pass


class PaysendApiError(PaysendError):
    """Error when the Paysend API returns an error response."""

    pass
