"""
URL patterns for the rate comparison API.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"compare", views.RateComparisonViewSet, basename="rates")

urlpatterns = [
    path("", include(router.urls)),
    path("send/", views.send_money_view, name="send_money"),
]
