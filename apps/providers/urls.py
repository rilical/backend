"""
URL patterns for the rate comparison API.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views_aggregator import AggregatorRatesView

router = DefaultRouter()
router.register(r'compare', views.RateComparisonViewSet, basename='rates')

urlpatterns = [
    path('', include(router.urls)),
    path('send/', views.send_money_view, name='send_money'),
    path('aggregator/rates/', AggregatorRatesView.as_view(), name='aggregator-rates'),
] 