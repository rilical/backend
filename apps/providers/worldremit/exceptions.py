"""
WorldRemit Exception Classes

This module defines all exception classes specific to the WorldRemit integration.
"""

class WorldRemitError(Exception):
    """Base exception class for WorldRemit-related errors."""
    pass

class WorldRemitAuthenticationError(WorldRemitError):
    """Raised when authentication with WorldRemit API fails."""
    pass

class WorldRemitConnectionError(WorldRemitError):
    """Raised when connection to WorldRemit API fails."""
    pass

class WorldRemitValidationError(WorldRemitError):
    """Raised when request validation fails."""
    pass

class WorldRemitRateLimitError(WorldRemitError):
    """Raised when API rate limit is exceeded."""
    pass 