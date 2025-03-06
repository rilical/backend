"""
Custom exceptions for the Remitbee integration.
"""

class RemitbeeError(Exception):
    """Base exception for all Remitbee-related errors."""
    pass


class RemitbeeConnectionError(RemitbeeError):
    """Raised when unable to connect to the Remitbee API."""
    pass


class RemitbeeApiError(RemitbeeError):
    """Raised when the Remitbee API returns an error."""
    pass


class RemitbeeValidationError(RemitbeeError):
    """Raised when input validation fails."""
    pass


class RemitbeeRateLimitError(RemitbeeError):
    """Raised when API rate limits are exceeded."""
    pass 