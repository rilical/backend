"""
Signal handlers for cache invalidation in the quotes app.

This module defines Django signal handlers that automatically invalidate
relevant cache entries when quote or provider data is updated or deleted.
This ensures data consistency across the caching layer.

Version: 1.0
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
    Invalidate quote cache entries when a FeeQuote is saved.
    
    This signal handler ensures that when quote data is updated in the database,
    corresponding cache entries are invalidated to prevent stale data from being
    served to clients.
    
    Args:
        sender: The model class that sent the signal (FeeQuote)
        instance: The actual instance being saved
        **kwargs: Additional arguments sent with the signal
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
        
        # Invalidate the specific quote cache
        cache.delete(cache_key)
        logger.info(f"Invalidated quote cache: {cache_key}")
        
        # Also invalidate the corridor rate cache since rates may have changed
        corridor_rate_key = get_corridor_rate_cache_key(
            instance.source_country,
            instance.destination_country,
            instance.source_currency,
            instance.destination_currency
        )
        cache.delete(corridor_rate_key)
        logger.info(f"Invalidated corridor rate cache: {corridor_rate_key}")
        
    except Exception as e:
        logger.error(f"Error invalidating quote cache: {str(e)}")


@receiver(post_delete, sender=FeeQuote)
def invalidate_quote_cache_on_delete(sender, instance, **kwargs):
    """
    Invalidate quote cache entries when a FeeQuote is deleted.
    
    Similar to the post_save handler, this ensures consistency when quotes
    are removed from the database.
    
    Args:
        sender: The model class that sent the signal (FeeQuote)
        instance: The actual instance being deleted
        **kwargs: Additional arguments sent with the signal
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
        
        # Invalidate the specific quote cache
        cache.delete(cache_key)
        logger.info(f"Invalidated quote cache on delete: {cache_key}")
        
        # Also check if we need to invalidate the corridor availability cache
        # If this was the last quote for this corridor, it might not be available anymore
        remaining_quotes = FeeQuote.objects.filter(
            source_country=instance.source_country,
            destination_country=instance.destination_country
        ).exists()
        
        if not remaining_quotes:
            corridor_key = get_corridor_cache_key(instance.source_country, instance.destination_country)
            cache.delete(corridor_key)
            logger.info(f"Invalidated corridor cache due to last quote deletion: {corridor_key}")
            
    except Exception as e:
        logger.error(f"Error invalidating quote cache on delete: {str(e)}")


@receiver(post_save, sender=Provider)
def invalidate_provider_cache(sender, instance, **kwargs):
    """
    Invalidate provider cache entries when a Provider is updated.
    
    This ensures that any provider data cached throughout the system
    is refreshed when the provider information changes.
    
    Args:
        sender: The model class that sent the signal (Provider)
        instance: The actual instance being saved
        **kwargs: Additional arguments sent with the signal
    """
    try:
        # Invalidate the provider's specific cache
        provider_key = get_provider_cache_key(instance.id)
        cache.delete(provider_key)
        logger.info(f"Invalidated provider cache: {provider_key}")
        
    except Exception as e:
        logger.error(f"Error invalidating provider cache: {str(e)}") 