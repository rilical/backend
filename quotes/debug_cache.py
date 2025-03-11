#!/usr/bin/env python
"""
Debug script to check cache key formatting in Django.
Run this with Django's runscript:
    python manage.py runscript debug_cache
"""

import logging
from django.core.cache import cache
from django.conf import settings
from .key_generators import get_quote_cache_key

logger = logging.getLogger(__name__)

def run():
    """Test cache key formatting and look up a specific key we set in Redis."""
    # Parameters matching our test case
    source_country = "GB"
    dest_country = "MX"
    source_currency = "GBP"
    dest_currency = "MXN"
    amount = 500.0
    
    # Generate the key as the code does
    cache_key = get_quote_cache_key(source_country, dest_country, source_currency, dest_currency, amount)
    
    # Print what we know about the cache
    print(f"Cache backend: {settings.CACHES['default']['BACKEND']}")
    print(f"Cache location: {settings.CACHES['default']['LOCATION']}")
    print(f"Cache key prefix: {settings.CACHES['default']['KEY_PREFIX']}")
    
    # See what's in the cache for this key
    print(f"\nGenerated key: {cache_key}")
    
    # Try to get this key
    value = cache.get(cache_key)
    print(f"Value for this key: {value}")
    
    # Set a test value
    test_value = {"test": True, "source_country": source_country}
    cache.set(cache_key, test_value, timeout=300)
    print(f"Set test value: {test_value}")
    
    # Verify we can get it back
    retrieved = cache.get(cache_key)
    print(f"Retrieved value: {retrieved}")
    
    # Test with a raw Redis key to see what's happening
    print("\nChecking Redis directly:")
    redis_client = cache.client._client
    full_key = f"{settings.CACHES['default']['KEY_PREFIX']}:1:{cache_key}"
    print(f"Full Redis key: {full_key}")
    
    # Get the key we manually set earlier via Redis CLI
    manual_key = f"remitscout:1:v1:fee:{source_country}:{dest_country}:{source_currency}:{dest_currency}:{float(amount)}"
    manual_value = redis_client.get(manual_key)
    print(f"Manual key: {manual_key}")
    print(f"Manual value: {manual_value}")
    
    # Try getting our test value again to confirm
    test_again = cache.get(cache_key)
    print(f"Test value retrieved again: {test_again}") 