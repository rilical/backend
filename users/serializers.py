from django.contrib.auth.models import User
from rest_framework import serializers

from .models import APIKey, UserProfile


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for UserProfile model."""

    class Meta:
        model = UserProfile
        fields = [
            "default_source_country",
            "default_source_currency",
            "default_destination_country",
            "default_destination_currency",
            "api_requests_count",
            "last_api_request",
            "created_at",
        ]
        read_only_fields = ["api_requests_count", "last_api_request", "created_at"]


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model with profile data."""

    profile = UserProfileSerializer()

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "profile"]
        read_only_fields = ["id"]

    def update(self, instance, validated_data):
        profile_data = validated_data.pop("profile", {})
        # Update User instance
        instance = super().update(instance, validated_data)

        # Update UserProfile instance
        if profile_data:
            profile = instance.profile
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()

        return instance


class APIKeySerializer(serializers.ModelSerializer):
    """Serializer for APIKey model."""

    class Meta:
        model = APIKey
        fields = ["id", "key", "name", "is_active", "created_at", "last_used"]
        read_only_fields = ["id", "key", "created_at", "last_used"]
