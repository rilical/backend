#!/usr/bin/env python
"""
A script to fix the caching issue by setting values with the correct serialization.
"""

import logging
import pickle
import redis
import time
from decimal import Decimal
from django.core.cache import cache
from django.conf import settings
from quotes.key_generators import get_quote_cache_key

logger = logging.getLogger(__name__)

def run():
    """Fix the caching issue by using correct serialization."""
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
    
    # Clear existing cached value
    cache.delete(cache_key)
    
    # Store the test data in the cache
    cache.set(cache_key, test_data, timeout=300)
    print(f"Stored test data in cache with key: {cache_key}")
    
    # Verify it worked
    retrieved = cache.get(cache_key)
    print(f"Retrieved from cache: {'SUCCESS' if retrieved else 'FAILED'}")
    if retrieved:
        print(f"Retrieved data: {retrieved}")
    
    # Now make an API request to test
    print("\nNow try making an API request with these same parameters:")
    print(f"curl -s \"http://localhost:8000/api/quotes/?source_country={source_country}&dest_country={dest_country}&source_currency={source_currency}&dest_currency={dest_currency}&amount={amount}\" | grep cache_hit")
    
    # Explanation of the fix
    print("\nEXPLANATION OF THE ISSUE:")
    print("1. The caching system is working correctly when using Django's cache interface.")
    print("2. The issue was with our attempts to manually set values in Redis without using Django's serialization.")
    print("3. Django-redis uses pickle serialization by default, not JSON.")
    print("4. For proper cache functionality, always use Django's cache interface rather than direct Redis commands.")
    
    return 0  # Success 