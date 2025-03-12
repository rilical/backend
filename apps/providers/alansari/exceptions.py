"""
Al Ansari Exchange provider exceptions.
"""


class AlAnsariError(Exception):
    """Base exception for Al Ansari Exchange provider."""

    pass


class AlAnsariAuthError(AlAnsariError):
    """Raised when authentication fails."""

    def __init__(self, message: str):
        super().__init__(message)


class AlAnsariApiError(AlAnsariError):
    """Raised when the API returns an error response."""

    def __init__(self, message: str, status_code: int = None, response: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class AlAnsariValidationError(AlAnsariError):
    """Raised when input validation fails."""

    pass


class AlAnsariConnectionError(AlAnsariError):
    """Raised when there are connection issues with the API."""

    pass


class AlAnsariRateLimitError(AlAnsariError):
    """Raised when API rate limits are exceeded."""

    pass


class AlAnsariResponseError(AlAnsariError):
    """Raised when there is an error parsing the API response."""

    pass


class AlAnsariCorridorUnsupportedError(AlAnsariError):
    """Raised when a requested corridor is not supported."""

    pass


class AlAnsariSecurityTokenError(AlAnsariError):
    """Raised when there is an error fetching or using the security token."""

    pass
