"""
WireBarley Provider Exceptions

This module defines custom exceptions for the WireBarley remittance provider integration.
Each exception corresponds to a specific error case in the integration flow.
"""

class WireBarleyError(Exception):
    """Base exception for all WireBarley-related errors."""
    pass

class WireBarleyAuthError(WireBarleyError):
    """Raised when authentication fails (invalid/expired credentials or session)."""
    pass

class WireBarleySessionError(WireBarleyError):
    """Raised when session validation fails or cannot be initialized."""
    pass

class WireBarleyAPIError(WireBarleyError):
    """
    Raised when the WireBarley API returns an error response.
    
    Attributes:
        status_code (int): HTTP status code from the API
        response (dict): Full API response for debugging
    """
    def __init__(self, message: str, status_code: int = None, response: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response

class WireBarleyRateError(WireBarleyError):
    """Raised when exchange rate fetching or parsing fails."""
    pass

class WireBarleyValidationError(WireBarleyError):
    """Raised when input validation fails (invalid currency, amount, etc)."""
    pass

class WireBarleyQuoteError(WireBarleyError):
    """Raised when quote generation fails."""
    pass

class WireBarleyCorridorError(WireBarleyError):
    """Raised when a requested corridor is not supported or unavailable."""
    pass

class WireBarleyThresholdError(WireBarleyError):
    """Raised when amount is outside supported thresholds for a corridor."""
    pass 