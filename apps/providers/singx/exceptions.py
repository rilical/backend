"""
SingX API Integration Exceptions

This module defines custom exceptions for the SingX remittance service integration.
These exceptions handle various error cases that may occur during API interactions.
"""

class SingXError(Exception):
    """Base exception for all SingX-related errors."""
    def __init__(self, message="An error occurred with SingX API", status_code=None, response=None):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(self.message)

class SingXAuthError(SingXError):
    """Raised when there are authentication issues with the SingX API."""
    def __init__(self, message="Authentication failed with SingX API", status_code=None, response=None):
        super().__init__(message, status_code, response)

class SingXAPIError(SingXError):
    """Raised when the SingX API returns an error response."""
    def __init__(self, message="API request failed", status_code=None, response=None):
        super().__init__(message, status_code, response)

class SingXValidationError(SingXError):
    """Raised when there are validation errors with the request parameters."""
    def __init__(self, message="Invalid parameters provided", status_code=None, response=None):
        super().__init__(message, status_code, response)

class SingXCorridorError(SingXError):
    """Raised when a requested corridor is not supported."""
    def __init__(self, message="Unsupported corridor", status_code=None, response=None):
        super().__init__(message, status_code, response)

class SingXQuoteError(SingXError):
    """Raised when there are issues getting a quote."""
    def __init__(self, message="Failed to get quote", status_code=None, response=None):
        super().__init__(message, status_code, response)

class SingXRateError(SingXError):
    """Raised when there are issues getting exchange rates."""
    def __init__(self, message="Failed to get exchange rate", status_code=None, response=None):
        super().__init__(message, status_code, response) 