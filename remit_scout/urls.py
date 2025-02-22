"""
URL configuration for the RemitScout project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/providers/', include('apps.providers.urls')),  # Rate comparison API
]
