from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"users", views.UserViewSet, basename="user")
router.register(r"api-keys", views.APIKeyViewSet, basename="api-key")

app_name = "users"

urlpatterns = [
    path("", include(router.urls)),
]
