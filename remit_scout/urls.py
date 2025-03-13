"""
URL configuration for the RemitScout project.
"""
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/providers/", include("providers.urls")),  # Rate comparison API
    path("api/quotes/", include("quotes.urls")),  # Quotes API
    # Removed aggregator API - redundant with quotes API

    # API Documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),  # API schema
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),  # Swagger UI
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),  # ReDoc UI
]
