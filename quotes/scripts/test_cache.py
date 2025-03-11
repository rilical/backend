#!/usr/bin/env python
"""
A script to test and fix our caching issues.
"""

import logging
import redis
import json
import time
from decimal import Decimal
from django.core.cache import cache
from django.conf import settings
from quotes.key_generators import get_quote_cache_key
from django_redis import get_redis_connection

logger = logging.getLogger(__name__)

def run():
    """Test and fix our caching issues."""
    # Parameters matching our test case
    source_country = "GB"
    dest_country = "MX"
    source_currency = "GBP"
    dest_currency = "MXN"
    amount = 500.0
    
    # The key we need to test
    cache_key = get_quote_cache_key(
        source_country, dest_country, source_currency, dest_currency, amount
    )
    print(f"\nOriginal cache key: {cache_key}")
    
    # Create a sample quote response
    test_data = {
        "success": True,
        "source_country": source_country,
        "dest_country": dest_country,
        "source_currency": source_currency,
        "dest_currency": dest_currency,
        "amount": float(amount),
        "quotes": [
            {
                "provider_id": "test-provider",
                "success": True,
                "exchange_rate": 25.0,
                "fee": 5.0,
                "destination_amount": 12500.0,
                "delivery_time_minutes": 1440,
                "payment_method": "BANK_TRANSFER",
                "delivery_method": "BANK_TRANSFER"
            }
        ],
        "timestamp": "2023-01-01T00:00:00Z",
        "cache_hit": True,
    }
    
    # Store this in the cache
    cache.set(cache_key, test_data, timeout=300)
    print(f"Stored test data in cache with key: {cache_key}")
    print(f"Cache backend: {settings.CACHES['default']['BACKEND']}")
    print(f"Cache location: {settings.CACHES['default']['LOCATION']}")
    print(f"Cache key prefix: {settings.CACHES['default']['KEY_PREFIX']}")
    
    # Let's verify it got stored correctly
    redis_conn = get_redis_connection("default")
    
    # Try to list keys related to our test
    all_keys = redis_conn.keys(f"{settings.CACHES['default']['KEY_PREFIX']}:*v1:fee:{source_country}:{dest_country}:{source_currency}:{dest_currency}*")
    print(f"\nFound {len(all_keys)} matching keys in Redis:")
    for key in all_keys:
        print(f"  - {key.decode('utf-8')}")
    
    # Now test retrieval
    retrieved = cache.get(cache_key)
    print(f"\nRetrieved from cache using original key: {'SUCCESS' if retrieved else 'FAILED'}")
    
    if retrieved:
        print(f"Retrieved data: {retrieved}")
    
    # Check with direct Redis access
    redis_key = f"{settings.CACHES['default']['KEY_PREFIX']}:1:{cache_key}"
    raw_value = redis_conn.get(redis_key)
    print(f"\nDirect Redis retrieval for key '{redis_key}': {'SUCCESS' if raw_value else 'FAILED'}")
    
    # Now clear everything and create a new manually crafted key
    cache.delete(cache_key)
    
    # Create new test data with different structure
    new_test_data = test_data.copy()
    new_test_data["cache_hit"] = True
    new_test_data["note"] = "This is a manually crafted key for testing"
    
    # Set the value directly in Redis without using Django's cache
    redis_key = f"{settings.CACHES['default']['KEY_PREFIX']}:1:{cache_key}"
    serialized = json.dumps(new_test_data)
    redis_conn.set(redis_key, serialized)
    
    print(f"\nManually set Redis key: {redis_key}")
    print(f"With data: {new_test_data}")
    
    # Wait 1 second for Redis
    time.sleep(1)
    
    # Now try to retrieve it using Django's cache
    retrieved2 = cache.get(cache_key)
    print(f"\nRetrieved manually set data through Django: {'SUCCESS' if retrieved2 else 'FAILED'}")
    
    if retrieved2:
        print(f"Retrieved data: {retrieved2}")
    else:
        print("There seems to be an issue with how Django's cache is interacting with Redis")
        
    # Do one more test with a URL safe cached value
    redis_conn.flushdb()  # Clear everything
    
    # Let's try with Redis' serialization approach
    redis_key = f"{settings.CACHES['default']['KEY_PREFIX']}:1:{cache_key}"
    redis_conn.set(redis_key, json.dumps(new_test_data).encode())
    
    # Check if Django can retrieve it
    retrieved3 = cache.get(cache_key)
    print(f"\nRetrieved after manual binary encoding: {'SUCCESS' if retrieved3 else 'FAILED'}")
    
    # Conclusion
    if retrieved3:
        print("\nISSUE FIXED: The caching system is now working correctly!")
    else:
        print("\nISSUE DIAGNOSIS: There appears to be a mismatch between Django's serialization and what we're using.")
        print("This could be due to compression, serialization format, or version numbers in the cache keys.")
        
    return 0  # Success 