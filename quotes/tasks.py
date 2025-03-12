"""
Celery tasks for the quotes app.

This module defines scheduled background tasks that handle cache management,
data cleanup, and other maintenance operations for the RemitScout quotes system.

Version: 1.0
"""
import logging
from datetime import timedelta
from decimal import Decimal

from celery import shared_task
from django.db.models import Count
from django.utils import timezone

from .cache_utils import invalidate_all_quote_caches, preload_corridor_caches, preload_quote_cache
from .models import FeeQuote, QuoteQueryLog

logger = logging.getLogger(__name__)


@shared_task
def refresh_popular_corridor_caches():
    """
    Refresh cache for popular corridors based on recent query patterns.

    This task analyzes user query logs to identify frequently requested
    corridors and preloads their cache data. This improves user experience
    by ensuring commonly accessed corridors have fresh data available.

    Schedule: Runs hourly
    """
    # Get corridors from the last 24 hours
    since = timezone.now() - timedelta(hours=24)

    # Count queries by corridor
    popular_corridors = (
        QuoteQueryLog.objects.filter(timestamp__gte=since)
        .values("source_country", "destination_country")
        .annotate(count=Count("id"))
        .order_by("-count")[:20]
    )  # Top 20 corridors

    # Refresh corridor caches
    for corridor in popular_corridors:
        source_country = corridor["source_country"]
        dest_country = corridor["destination_country"]
        logger.info(f"Refreshing popular corridor cache: {source_country} → {dest_country}")

        # Get quotes for this corridor
        quotes = FeeQuote.objects.filter(
            source_country=source_country, destination_country=dest_country
        ).distinct("provider_id")[
            :5
        ]  # Limit to 5 per provider

    logger.info(f"Refreshed caches for {len(popular_corridors)} popular corridors")


@shared_task
def refresh_popular_quote_caches():
    """
    Refresh cache for popular quote requests based on recent query logs.

    This task identifies the most frequently requested quote combinations
    (corridor + currencies + amount) and preloads their specific cache
    entries to ensure fast response times for common requests.

    Schedule: Runs every 2 hours
    """
    # Look at the last 48 hours
    since = timezone.now() - timedelta(hours=48)

    # Find the most popular quote combinations
    popular_quotes = (
        QuoteQueryLog.objects.filter(timestamp__gte=since)
        .values(
            "source_country",
            "destination_country",
            "source_currency",
            "destination_currency",
            "send_amount",
        )
        .annotate(count=Count("id"))
        .order_by("-count")[:50]
    )  # Top 50 combinations

    # Preload each popular quote combination
    for quote_params in popular_quotes:
        try:
            # Check if we have recent fee quotes for this
            recent_quotes = FeeQuote.objects.filter(
                source_country=quote_params["source_country"],
                destination_country=quote_params["destination_country"],
                source_currency=quote_params["source_currency"],
                destination_currency=quote_params["destination_currency"],
                send_amount=quote_params["send_amount"],
                last_updated__gte=timezone.now() - timedelta(hours=24),
            )

            if recent_quotes.exists():
                logger.info(f"Preloading quote cache for {quote_params}")
                for quote in recent_quotes:
                    preload_quote_cache(quote)
        except Exception as e:
            logger.error(f"Error preloading quote cache: {str(e)}")

    logger.info(f"Refreshed caches for {len(popular_quotes)} popular quote combinations")


@shared_task
def clean_old_quotes():
    """
    Remove outdated quote data from the database.

    This task performs database maintenance by deleting fee quotes that are
    outdated and unlikely to be relevant anymore. This keeps the database size
    manageable and improves query performance.

    Schedule: Runs daily
    """
    # Keep quotes from the last 7 days
    cutoff_date = timezone.now() - timedelta(days=7)

    # Count quotes before deletion
    total_quotes = FeeQuote.objects.count()

    # Delete old quotes
    old_quotes = FeeQuote.objects.filter(last_updated__lt=cutoff_date)
    deleted_count = old_quotes.count()
    old_quotes.delete()

    logger.info(f"Cleaned {deleted_count} old quotes (retained {total_quotes - deleted_count})")

    return deleted_count


@shared_task
def refresh_cache_daily():
    """
    Perform full cache refresh and database maintenance.

    This comprehensive task performs a full cache reset and ensures
    fresh data is loaded for all active corridors. It also triggers
    database cleanup operations.

    Schedule: Runs daily during off-peak hours
    """
    logger.info("Starting daily cache refresh")

    # First, clean up old quotes
    cleaned = clean_old_quotes.delay()

    # Completely invalidate and rebuild the cache
    invalidate_all_quote_caches()

    # Preload corridor availability info
    preload_corridor_caches()

    # Refresh popular quotes
    refresh_popular_quote_caches.delay()

    logger.info("Completed daily cache refresh")

    return True
