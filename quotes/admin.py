"""
Django admin configuration for the quotes app.

This module defines the admin interface for the quote-related models, allowing
administrators to manage providers, fee quotes, and query logs.

Version: 1.0
"""
from django.contrib import admin
from .models import Provider, FeeQuote, QuoteQueryLog


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    """Admin configuration for the Provider model."""
    list_display = ('id', 'name', 'active', 'updated_at')
    list_filter = ('active',)
    search_fields = ('id', 'name')
    ordering = ('name',)


@admin.register(FeeQuote)
class FeeQuoteAdmin(admin.ModelAdmin):
    """
    Admin configuration for the FeeQuote model.
    
    Provides a comprehensive interface for viewing and filtering fee quotes
    from various providers and corridors.
    """
    list_display = (
        'provider', 'source_country', 'destination_country', 
        'source_currency', 'destination_currency', 'send_amount',
        'fee_amount', 'exchange_rate', 'delivery_time_minutes',
        'last_updated'
    )
    list_filter = (
        'provider', 'source_country', 'destination_country',
        'payment_method', 'delivery_method'
    )
    search_fields = (
        'provider__name', 'source_country', 'destination_country'
    )
    date_hierarchy = 'last_updated'
    ordering = ('-last_updated',)


@admin.register(QuoteQueryLog)
class QuoteQueryLogAdmin(admin.ModelAdmin):
    """
    Admin configuration for the QuoteQueryLog model.
    
    Provides an interface for analyzing user query patterns while
    maintaining privacy by making IP addresses read-only.
    """
    list_display = (
        'source_country', 'destination_country', 
        'source_currency', 'destination_currency',
        'send_amount', 'timestamp'
    )
    list_filter = ('source_country', 'destination_country')
    date_hierarchy = 'timestamp'
    readonly_fields = ('user_ip',)  # For privacy, make IP read-only 