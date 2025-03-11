#!/usr/bin/env python
"""
Debug script to test the quote caching functionality.
Run with: python manage.py runscript debug_cache
"""
import logging
import json
import redis
from django.conf import settings
from django.core.cache import cache

from quotes.key_generators import get_quote_cache_key

logger = logging.getLogger(__name__)

def run():
    """Test the quote caching functionality"""
    # Test parameters
    source_country = "GB"
    dest_country = "MX"
    source_currency = "GBP"
    dest_currency = "MXN"
    amount = 500.0
    
    # 1. Generate cache key
    cache_key = get_quote_cache_key(source_country, dest_country, source_currency, dest_currency, amount)
    print(f"Generated cache key: {cache_key}")
    
    # Create a simple test structure
    test_data = {
        "success": True,
        "cache_test": "This is a test cache entry",
        "amount": amount,
        "source_country": source_country,
        "dest_country": dest_country,
        "source_currency": source_currency,
        "dest_currency": dest_currency,
    }
    
    # 2. Try to set the value in the cache
    result = cache.set(cache_key, test_data, timeout=300)
    print(f"Result of cache.set: {result}")
    
    # 3. Try to retrieve the value from the cache
    cached_data = cache.get(cache_key)
    print(f"Cache hit: {cached_data is not None}")
    if cached_data:
        print(f"Retrieved from cache: {cached_data.get('cache_test')}")
    
    # 4. Check Redis directly
    try:
        r = redis.Redis(host='localhost', port=6379, db=1)
        redis_key = f"remitscout:1:{cache_key}"
        exists = r.exists(redis_key)
        print(f"Redis key exists: {exists}")
        
        # Retrieve all keys in Redis
        all_keys = r.keys("remitscout:1:*")
        print(f"All keys in Redis ({len(all_keys)}): {all_keys}")
    except Exception as e:
        print(f"Error checking Redis directly: {e}") 