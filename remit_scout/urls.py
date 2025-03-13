"""
URL configuration for the RemitScout project.
"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/providers/", include("providers.urls")),  # Rate comparison API
    path("api/quotes/", include("quotes.urls")),  # Quotes API
]
