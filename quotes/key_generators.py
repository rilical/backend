"""
Cache key generator functions for the quotes app.

This module provides standardized functions for generating deterministic cache keys
used throughout the RemitScout caching system.

Version: 1.0
"""
import logging

logger = logging.getLogger(__name__)


def get_quote_cache_key(source_country, dest_country, source_currency, dest_currency, amount):
    """Generate a deterministic cache key for quote queries."""
    return (
        f"v1:fee:{source_country}:{dest_country}:{source_currency}:{dest_currency}:{float(amount)}"
    )


def get_provider_cache_key(provider_id):
    """Generate a cache key for provider data."""
    return f"provider:{provider_id}"


def get_corridor_cache_key(source_country, dest_country):
    """Generate a cache key for corridor data."""
    return f"corridor:{source_country}:{dest_country}"


def get_corridor_rate_cache_key(source_country, dest_country, source_currency, dest_currency):
    """Generate a cache key for corridor rate data."""
    return f"corridor_rate:{source_country}:{dest_country}:{source_currency}:{dest_currency}"
