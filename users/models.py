from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    """
    Extended user profile for RemitScout.
    Stores additional user information not covered by Django's built-in User model.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )

    # Additional fields
    default_source_country = models.CharField(max_length=2, blank=True, null=True)
    default_source_currency = models.CharField(max_length=3, blank=True, null=True)
    default_destination_country = models.CharField(max_length=2, blank=True, null=True)
    default_destination_currency = models.CharField(max_length=3, blank=True, null=True)

    # API usage tracking
    api_requests_count = models.PositiveIntegerField(default=0)
    last_api_request = models.DateTimeField(blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s profile"


class APIKey(models.Model):
    """
    API keys for accessing the RemitScout API.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="api_keys"
    )
    key = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=100)  # A name to identify what this key is for
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.user.username})"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a UserProfile automatically when a User is created."""
    if created:
        UserProfile.objects.create(user=instance)
