"""
URL patterns for the aggregator API.

This module defines the URL routing configuration for the RemitScout aggregator API,
which combines quotes from multiple remittance providers.
"""
from django.urls import path

from .views import AggregatorRatesView

app_name = "aggregator"

urlpatterns = [
    # Main aggregator endpoint is removed since it's redundant with quotes endpoint
    # All remittance quotes are available through the quotes endpoint instead
] 