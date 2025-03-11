"""
Celery tasks for the quotes app.
"""
import logging
from datetime import timedelta
from celery import shared_task
from django.utils import timezone
from django.db.models import Count
from decimal import Decimal

from .models import FeeQuote, QuoteQueryLog
from .cache_utils import (
    preload_corridor_caches,
    preload_quote_cache,
    invalidate_all_quote_caches
)

logger = logging.getLogger(__name__)

@shared_task
def refresh_popular_corridor_caches():
    """
    Identify popular corridors from recent queries and refresh their caches.
    This task should run periodically (e.g., every hour) to ensure that
    popular corridors have fresh data in the cache.
    """
    # Get corridors from the last 24 hours
    since = timezone.now() - timedelta(hours=24)
    
    # Count queries by corridor
    popular_corridors = (
        QuoteQueryLog.objects
        .filter(timestamp__gte=since)
        .values('source_country', 'destination_country')
        .annotate(count=Count('id'))
        .order_by('-count')[:20]  # Top 20 corridors
    )
    
    # Preload corridor caches
    for corridor in popular_corridors:
        logger.info(f"Refreshing cache for popular corridor: {corridor['source_country']}->{corridor['destination_country']}")
        
    # Refresh corridor availability
    count = preload_corridor_caches()
    logger.info(f"Refreshed {count} corridor caches")
    
    return f"Refreshed caches for {count} corridors"


@shared_task
def refresh_popular_quote_caches():
    """
    Identify the most queried quote parameters and refresh their caches.
    This ensures that common quotes are always available from cache.
    """
    # Get popular queries from the last 24 hours
    since = timezone.now() - timedelta(hours=24)
    
    # Find popular queries
    popular_queries = (
        QuoteQueryLog.objects
        .filter(timestamp__gte=since)
        .values('source_country', 'destination_country', 'source_currency', 'destination_currency', 'send_amount')
        .annotate(count=Count('id'))
        .order_by('-count')[:50]  # Top 50 queries
    )
    
    # For each popular query, find a matching FeeQuote and preload its cache
    for query in popular_queries:
        try:
            # Find a matching quote
            quotes = FeeQuote.objects.filter(
                source_country=query['source_country'],
                destination_country=query['destination_country'],
                source_currency=query['source_currency'],
                destination_currency=query['destination_currency'],
                send_amount=query['send_amount']
            ).order_by('-last_updated')
            
            if quotes.exists():
                logger.info(f"Refreshing cache for popular quote: {query['source_country']}->{query['destination_country']} ({query['send_amount']} {query['source_currency']})")
                for quote in quotes[:5]:  # Preload top 5 provider quotes
                    preload_quote_cache(quote)
                    
        except Exception as e:
            logger.error(f"Error refreshing quote cache: {str(e)}")
    
    return f"Refreshed caches for {len(popular_queries)} popular queries"


@shared_task
def clean_old_quotes():
    """
    Remove quotes older than a certain threshold.
    This helps keep the database size manageable.
    """
    # Delete quotes older than 30 days
    threshold = timezone.now() - timedelta(days=30)
    
    # Count quotes to delete
    old_quotes_count = FeeQuote.objects.filter(last_updated__lt=threshold).count()
    
    # Delete them
    if old_quotes_count > 0:
        FeeQuote.objects.filter(last_updated__lt=threshold).delete()
        logger.info(f"Deleted {old_quotes_count} quotes older than 30 days")
    
    return f"Deleted {old_quotes_count} old quotes"


@shared_task
def refresh_cache_daily():
    """
    Perform a complete cache refresh once a day.
    This ensures that long-lived cached data doesn't become stale.
    """
    try:
        # Invalidate all caches
        invalidate_all_quote_caches()
        logger.info("Invalidated all quote caches for daily refresh")
        
        # Preload corridor caches
        count = preload_corridor_caches()
        logger.info(f"Preloaded {count} corridor caches for daily refresh")
        
        return "Daily cache refresh completed successfully"
    except Exception as e:
        logger.error(f"Error during daily cache refresh: {str(e)}")
        return f"Error during daily cache refresh: {str(e)}" 