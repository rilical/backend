"""
URL patterns for the quotes app.

This module defines the URL routing configuration for the RemitScout quotes API.

Version: 1.0
"""
from django.urls import path

from .views import QuoteAPIView

app_name = "quotes"

urlpatterns = [
    # Main quotes API endpoint that handles quote retrieval requests
    path("", QuoteAPIView.as_view(), name="quotes-api"),
]
