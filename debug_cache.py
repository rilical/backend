#!/usr/bin/env python
"""
Debug script for Django cache.
Run with: python debug_cache.py
"""

import os
import sys
import django
import redis
from decimal import Decimal

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'remit_scout.settings')
django.setup()

from django.core.cache import cache
from django.conf import settings

def test_cache():
    print("\nTesting Django Cache System...")
    # Generate test key
    test_key = "v1:fee:GB:MX:GBP:MXN:500.0"
    test_data = {
        "success": True,
        "test": "data",
        "amount": 500.0,
        "cache_hit": False
    }
    
    print(f"1. Setting cache with key: {test_key}")
    cache.set(test_key, test_data, timeout=300)
    
    print(f"2. Getting cache with key: {test_key}")
    cached_data = cache.get(test_key)
    print(f"   Cache hit: {cached_data is not None}")
    if cached_data:
        print(f"   Cached data: {cached_data}")
    
    # Check direct Redis lookup
    redis_client = redis.Redis.from_url(settings.CACHES['default']['LOCATION'])
    prefix = settings.CACHES['default']['KEY_PREFIX']
    redis_key = f"{prefix}:1:{test_key}"
    
    print(f"\n3. Direct Redis lookup with key: {redis_key}")
    redis_data = redis_client.get(redis_key)
    print(f"   Redis hit: {redis_data is not None}")
    
    # Check all keys in Redis
    print("\n4. All keys in Redis:")
    all_keys = redis_client.keys("*")
    if all_keys:
        for key in all_keys:
            print(f"   {key.decode('utf-8')}")
    else:
        print("   No keys found in Redis")

if __name__ == "__main__":
    test_cache() 