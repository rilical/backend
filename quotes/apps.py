"""
Django app configuration for the quotes module.

This module defines the app configuration for the quotes app, which is responsible
for handling and caching remittance quote data.

Version: 1.0
"""
from django.apps import AppConfig


class QuotesConfig(AppConfig):
    """
    Django app configuration for the quotes module.
    
    Handles app initialization and signal registration for the quotes system.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'quotes'
    
    def ready(self):
        """
        Import signal handlers when the app is ready.
        This ensures that the signal connections are established for cache invalidation.
        """
        import quotes.signals  # noqa 