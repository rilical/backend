"""
URL patterns for the rate comparison API.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
# Removed compare endpoint - redundant with quotes endpoint
# Register only the provider-specific endpoints
router.register(r"providers", views.RateComparisonViewSet, basename="providers")

urlpatterns = [
    path("", include(router.urls)),
    path("send/", views.send_money_view, name="send_money"),
]
