"""
Signal handlers for cache invalidation in the quotes app.
"""
import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from django.conf import settings

from .models import Provider, FeeQuote
from .key_generators import (
    get_quote_cache_key, get_provider_cache_key, 
    get_corridor_cache_key, get_corridor_rate_cache_key
)

logger = logging.getLogger(__name__)

@receiver(post_save, sender=FeeQuote)
def invalidate_quote_cache(sender, instance, **kwargs):
    """
    When a FeeQuote model is saved, invalidate the corresponding cache entries.
    This ensures that clients get the latest data after updates.
    """
    try:
        # Generate the cache key for this quote
        cache_key = get_quote_cache_key(
            instance.source_country,
            instance.destination_country,
            instance.source_currency, 
            instance.destination_currency,
            instance.send_amount
        )
        
        # Delete the specific cache entry
        cache.delete(cache_key)
        
        # Also invalidate the corridor rate cache to ensure fresh rates
        corridor_rate_key = get_corridor_rate_cache_key(
            instance.source_country,
            instance.destination_country,
            instance.source_currency,
            instance.destination_currency
        )
        cache.delete(corridor_rate_key)
        
        # Also invalidate the corridor cache
        corridor_key = get_corridor_cache_key(
            instance.source_country,
            instance.destination_country
        )
        cache.delete(corridor_key)
        
        logger.info(f"Cache invalidated for key: {cache_key} and corridor rate key: {corridor_rate_key}")
    except Exception as e:
        logger.warning(f"Error invalidating cache: {str(e)}")

@receiver(post_delete, sender=FeeQuote)
def invalidate_quote_cache_on_delete(sender, instance, **kwargs):
    """When a FeeQuote is deleted, invalidate related cache entries."""
    try:
        # Generate the cache key for this quote
        cache_key = get_quote_cache_key(
            instance.source_country,
            instance.destination_country,
            instance.source_currency, 
            instance.destination_currency,
            instance.send_amount
        )
        
        # Delete the specific cache entry
        cache.delete(cache_key)
        
        # Also invalidate the corridor rate cache to ensure fresh rates
        corridor_rate_key = get_corridor_rate_cache_key(
            instance.source_country,
            instance.destination_country,
            instance.source_currency,
            instance.destination_currency
        )
        cache.delete(corridor_rate_key)
        
        logger.info(f"Cache invalidated for deleted quote: {cache_key} and corridor rate key: {corridor_rate_key}")
    except Exception as e:
        logger.warning(f"Error invalidating cache on delete: {str(e)}")

@receiver(post_save, sender=Provider)
def invalidate_provider_cache(sender, instance, **kwargs):
    """When a Provider is updated, invalidate the provider cache."""
    try:
        # Generate the cache key for this provider
        cache_key = get_provider_cache_key(instance.id)
        
        # Delete the provider cache
        cache.delete(cache_key)
        
        logger.info(f"Provider cache invalidated: {cache_key}")
    except Exception as e:
        logger.warning(f"Error invalidating provider cache: {str(e)}") 