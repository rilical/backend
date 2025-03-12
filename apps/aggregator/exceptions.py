"""Exceptions for the aggregator module"""

from typing import Any, Dict, Optional


class AggregatorError(Exception):
    """Base exception for all aggregator-related errors."""

    def __init__(
        self,
        message: str = "An error occurred in the aggregator",
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class NoProvidersAvailableError(AggregatorError):
    """No providers available for a corridor."""

    def __init__(
        self,
        message: str = "No providers available for this corridor",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, details)


class QuoteFetchError(AggregatorError):
    """Error fetching quotes from providers."""

    def __init__(
        self,
        message: str = "Error fetching quotes from providers",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, details)


class InvalidCorridorError(AggregatorError):
    """Invalid corridor specified."""

    def __init__(
        self,
        message: str = "Invalid corridor specified",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, details)


class NoSuccessfulQuotesError(AggregatorError):
    """All provider quotes failed."""

    def __init__(
        self,
        message: str = "No successful quotes were obtained",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, details)
