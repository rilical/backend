"""
OrbitRemit provider-specific exceptions.

This module defines custom exceptions for the OrbitRemit provider integration.
"""


class OrbitRemitError(Exception):
    """Base exception for all OrbitRemit-related errors."""

    pass


class OrbitRemitConnectionError(OrbitRemitError):
    """Raised when there is a connection error with the OrbitRemit API."""

    pass


class OrbitRemitApiError(OrbitRemitError):
    """Raised when the OrbitRemit API returns an error response."""

    pass


class OrbitRemitResponseError(OrbitRemitError):
    """Raised when there is an error parsing the OrbitRemit API response."""

    pass


class OrbitRemitCorridorUnsupportedError(OrbitRemitError):
    """Raised when a requested corridor is not supported by OrbitRemit."""

    pass
