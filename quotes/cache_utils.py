"""
Cache utility functions for the quotes app.

This module provides functions for manual cache operations, 
such as invalidating caches by pattern, preloading caches, etc.
"""
import logging
import random
from django.core.cache import cache, caches
from django.conf import settings
from decimal import Decimal

from .models import FeeQuote, Provider
from .key_generators import (
    get_quote_cache_key, get_provider_cache_key, 
    get_corridor_cache_key, get_corridor_rate_cache_key
)

logger = logging.getLogger(__name__)

# New function to cache corridor rate information
def cache_corridor_rate_data(source_country, dest_country, source_currency, dest_currency, provider_data):
    """
    Cache the invariant rate information for a corridor.
    
    Args:
        source_country: Source country code
        dest_country: Destination country code
        source_currency: Source currency code
        dest_currency: Destination currency code
        provider_data: List of provider data dictionaries with rate information
        
    Returns:
        The cache key that was set
    """
    key = get_corridor_rate_cache_key(source_country, dest_country, source_currency, dest_currency)
    
    # Extract only the invariant data from each provider
    invariant_data = []
    for provider in provider_data:
        if not provider.get('success', False):
            continue
            
        # Extract the base data that doesn't change with the amount
        provider_invariant = {
            'provider_id': provider.get('provider_id'),
            'exchange_rate': provider.get('exchange_rate'),
            'delivery_time_minutes': provider.get('delivery_time_minutes'),
            'payment_method': provider.get('payment_method', 'card'),
            'delivery_method': provider.get('delivery_method', 'bank_deposit'),
            # Fee structure information
            'fee_type': provider.get('fee_type', 'fixed'),  # 'fixed' or 'percentage'
            'fee_value': provider.get('fee', 0),  # Either fixed amount or percentage
            'fee_percentage': provider.get('fee_percentage', 0),
            'min_fee': provider.get('min_fee', 0),
            'max_fee': provider.get('max_fee', None)
        }
        invariant_data.append(provider_invariant)
    
    # Add jitter to TTL to prevent thundering herd problem
    jitter = random.randint(-settings.JITTER_MAX_SECONDS, settings.JITTER_MAX_SECONDS)
    ttl = getattr(settings, 'CORRIDOR_RATE_CACHE_TTL', 60 * 30) + jitter  # Default 30 minutes
    
    cache.set(key, {
        'providers': invariant_data,
        'timestamp': provider_data[0].get('timestamp') if provider_data else None,
        'source_country': source_country,
        'dest_country': dest_country,
        'source_currency': source_currency,
        'dest_currency': dest_currency
    }, timeout=ttl)
    
    logger.info(f"Cached corridor rate data for {len(invariant_data)} providers with key: {key}")
    return key

# New function to get and use corridor rate information
def get_quotes_from_corridor_rates(source_country, dest_country, source_currency, dest_currency, amount):
    """
    Get quotes for a specific amount using cached corridor rate information.
    This avoids calling the providers when only the amount changes.
    
    Args:
        source_country: Source country code
        dest_country: Destination country code
        source_currency: Source currency code
        dest_currency: Destination currency code
        amount: Decimal amount to send
        
    Returns:
        A dictionary with quote information and a cache_hit flag,
        or None if no cached rate information is available
    """
    key = get_corridor_rate_cache_key(source_country, dest_country, source_currency, dest_currency)
    rate_data = cache.get(key)
    
    if not rate_data:
        logger.info(f"No cached corridor rate data for key: {key}")
        return None
    
    logger.info(f"Using cached corridor rate data for {len(rate_data.get('providers', []))} providers")
    
    # Calculate amounts for each provider based on cached rates
    quotes = []
    for provider in rate_data.get('providers', []):
        try:
            provider_id = provider.get('provider_id')
            exchange_rate = provider.get('exchange_rate', 0)
            
            # Calculate fee based on fee structure
            if provider.get('fee_type') == 'percentage':
                percentage = provider.get('fee_percentage', 0)
                fee = float(amount) * percentage / 100
                
                # Apply min/max constraints if present
                min_fee = provider.get('min_fee')
                max_fee = provider.get('max_fee')
                
                if min_fee is not None and fee < min_fee:
                    fee = min_fee
                if max_fee is not None and fee > max_fee:
                    fee = max_fee
            else:
                # Fixed fee
                fee = provider.get('fee_value', 0)
            
            # Calculate destination amount after fee
            send_amount = float(amount)
            destination_amount = (send_amount - fee) * exchange_rate
            
            quotes.append({
                'provider_id': provider_id,
                'success': True,
                'exchange_rate': exchange_rate,
                'fee': fee,
                'source_amount': send_amount,
                'destination_amount': destination_amount,
                'delivery_time_minutes': provider.get('delivery_time_minutes'),
                'payment_method': provider.get('payment_method'),
                'delivery_method': provider.get('delivery_method')
            })
        except Exception as e:
            logger.warning(f"Error calculating amounts for provider {provider.get('provider_id')}: {str(e)}")
    
    return {
        'success': len(quotes) > 0,
        'source_country': source_country,
        'dest_country': dest_country,
        'source_currency': source_currency,
        'dest_currency': dest_currency,
        'amount': float(amount),
        'quotes': quotes,
        'timestamp': rate_data.get('timestamp'),
        'cache_hit': True,
        'rate_calculation': True  # Flag to indicate this was calculated from rate cache
    }

def invalidate_all_quote_caches():
    """
    Invalidate all quote-related caches.
    Use with caution - this will force recalculation of all quotes.
    """
    cache.delete_pattern("v1:fee:*")
    cache.delete_pattern("v1:corridor_rates:*")  # Also invalidate corridor rate caches
    logger.info("Invalidated all quote caches")

def invalidate_corridor_caches(source_country=None, dest_country=None):
    """
    Invalidate caches for a specific corridor or all corridors.
    
    Args:
        source_country: Optional source country (if None, all sources are invalidated)
        dest_country: Optional destination country (if None, all destinations are invalidated)
    """
    if source_country and dest_country:
        # Invalidate a specific corridor
        key = get_corridor_cache_key(source_country, dest_country)
        cache.delete(key)
        logger.info(f"Invalidated corridor cache for {source_country}->{dest_country}")
    elif source_country:
        # Invalidate all corridors from a specific source
        cache.delete_pattern(f"corridor:{source_country}:*")
        logger.info(f"Invalidated all corridor caches from {source_country}")
    elif dest_country:
        # This is less efficient but we don't have a better pattern matching option
        corridors = FeeQuote.objects.filter(destination_country=dest_country).values_list(
            'source_country', 'destination_country').distinct()
        for src, dst in corridors:
            key = get_corridor_cache_key(src, dst)
            cache.delete(key)
        logger.info(f"Invalidated all corridor caches to {dest_country}")
    else:
        # Invalidate all corridors
        cache.delete_pattern("corridor:*")
        logger.info("Invalidated all corridor caches")

def invalidate_provider_caches(provider_id=None):
    """
    Invalidate provider caches.
    
    Args:
        provider_id: Optional provider ID (if None, all providers are invalidated)
    """
    if provider_id:
        key = get_provider_cache_key(provider_id)
        cache.delete(key)
        logger.info(f"Invalidated provider cache for {provider_id}")
    else:
        cache.delete_pattern("provider:*")
        logger.info("Invalidated all provider caches")

def preload_corridor_caches():
    """
    Preload corridor availability information into the cache.
    This helps avoid unnecessary API calls for unsupported corridors.
    """
    # Get all corridors that have at least one successful quote
    corridors = FeeQuote.objects.values_list(
        'source_country', 'destination_country').distinct()
    
    count = 0
    for source_country, dest_country in corridors:
        key = get_corridor_cache_key(source_country, dest_country)
        # Add a small jitter to TTL to prevent thundering herd problem
        jitter = random.randint(-settings.JITTER_MAX_SECONDS, settings.JITTER_MAX_SECONDS)
        ttl = settings.CORRIDOR_CACHE_TTL + jitter
        
        cache.set(key, True, timeout=ttl)
        count += 1
    
    logger.info(f"Preloaded {count} corridor caches")
    return count

def preload_quote_cache(quote):
    """
    Manually preload a quote into the cache.
    
    Args:
        quote: A FeeQuote instance to preload
    
    Returns:
        The cache key that was set
    """
    key = get_quote_cache_key(
        quote.source_country,
        quote.destination_country,
        quote.source_currency,
        quote.destination_currency,
        quote.send_amount
    )
    
    # Build a response similar to what the API would return
    response = {
        "success": True,
        "source_country": quote.source_country,
        "dest_country": quote.destination_country,
        "source_currency": quote.source_currency,
        "dest_currency": quote.destination_currency,
        "amount": float(quote.send_amount),
        "quotes": [
            {
                "provider_id": quote.provider.id,
                "success": True,
                "exchange_rate": float(quote.exchange_rate),
                "fee": float(quote.fee_amount),
                "destination_amount": float(quote.destination_amount),
                "delivery_time_minutes": quote.delivery_time_minutes,
                "payment_method": quote.payment_method,
                "delivery_method": quote.delivery_method
            }
        ],
        "timestamp": quote.last_updated.isoformat(),
        "cache_hit": False,
    }
    
    # Add jitter to TTL to prevent thundering herd problem
    jitter = random.randint(-settings.JITTER_MAX_SECONDS, settings.JITTER_MAX_SECONDS)
    ttl = settings.QUOTE_CACHE_TTL + jitter
    
    cache.set(key, response, timeout=ttl)
    logger.info(f"Preloaded quote cache for key: {key}")
    
    return key 