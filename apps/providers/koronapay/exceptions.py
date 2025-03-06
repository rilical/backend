"""
KoronaPay Provider Exceptions

This module defines custom exceptions for the KoronaPay remittance provider integration.
Each exception corresponds to a specific error case in the integration flow.
"""

class KoronaPayError(Exception):
    """Base exception for all KoronaPay-related errors."""
    pass

class KoronaPayAuthError(KoronaPayError):
    """Raised when authentication fails (invalid/expired credentials or session)."""
    pass

class KoronaPaySessionError(KoronaPayError):
    """Raised when session validation fails or cannot be initialized."""
    pass

class KoronaPayAPIError(KoronaPayError):
    """
    Raised when the KoronaPay API returns an error response.
    
    Attributes:
        status_code (int): HTTP status code from the API
        response (dict): Full API response for debugging
    """
    def __init__(self, message: str, status_code: int = None, response: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response

class KoronaPayRateError(KoronaPayError):
    """Raised when exchange rate fetching or parsing fails."""
    pass

class KoronaPayValidationError(KoronaPayError):
    """Raised when input validation fails (invalid country, currency, amount, etc)."""
    pass

class KoronaPayQuoteError(KoronaPayError):
    """Raised when quote generation fails."""
    pass

class KoronaPayCorridorError(KoronaPayError):
    """Raised when a requested corridor is not supported or unavailable."""
    pass

class KoronaPayPaymentMethodError(KoronaPayError):
    """Raised when an unsupported payment or receiving method is requested."""
    pass 