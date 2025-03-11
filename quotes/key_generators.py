"""
Cache key generator functions for the quotes app.

This module contains functions for generating deterministic cache keys
for various caching operations in the quotes system.
"""
import logging

logger = logging.getLogger(__name__)

def get_quote_cache_key(source_country, dest_country, source_currency, dest_currency, amount):
    """
    Generate a deterministic cache key for quote queries.
    This should match the key generation in the QuoteAPIView.
    """
    return f"v1:fee:{source_country}:{dest_country}:{source_currency}:{dest_currency}:{float(amount)}"

def get_provider_cache_key(provider_id):
    """Generate a cache key for provider data."""
    return f"provider:{provider_id}"

def get_corridor_cache_key(source_country, dest_country):
    """Generate a cache key for corridor availability."""
    return f"corridor:{source_country}:{dest_country}"

def get_corridor_rate_cache_key(source_country, dest_country, source_currency, dest_currency):
    """
    Generate a cache key for corridor rate information independent of amount.
    This caches the invariant data (exchange rates, fee structures, delivery times)
    that doesn't change with the amount.
    """
    return f"v1:corridor_rates:{source_country}:{dest_country}:{source_currency}:{dest_currency}" 