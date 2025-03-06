"""
Intermex provider exceptions.
"""

class IntermexError(Exception):
    """Base exception for Intermex provider."""
    pass

class IntermexAuthError(IntermexError):
    """Raised when authentication with Intermex API fails."""
    def __init__(self, message: str):
        super().__init__(message)

class IntermexAPIError(IntermexError):
    """Raised when Intermex API returns an error response."""
    def __init__(self, message: str, status_code: int = None, response: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response

class IntermexValidationError(IntermexError):
    """Raised when input validation fails."""
    pass

class IntermexConnectionError(IntermexError):
    """Raised when we can't connect to Intermex's API."""
    pass

class IntermexRateLimitError(IntermexError):
    """Raised when we exceed the API rate limits."""
    pass 