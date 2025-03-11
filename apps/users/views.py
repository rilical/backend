from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth.models import User
from django.utils import timezone
import uuid
import base64
import hashlib

from .models import UserProfile, APIKey
from .serializers import UserSerializer, UserProfileSerializer, APIKeySerializer


class UserViewSet(viewsets.ModelViewSet):
    """API endpoint for user management."""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Users can only see their own profile."""
        user = self.request.user
        if user.is_staff:
            return User.objects.all()
        return User.objects.filter(id=user.id)
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get the current user's data."""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


class APIKeyViewSet(viewsets.ModelViewSet):
    """API endpoint for managing API keys."""
    serializer_class = APIKeySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Users can only see their own API keys."""
        return APIKey.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        """Generate a new API key and save it."""
        # Generate a secure random key
        random_key = uuid.uuid4().hex + uuid.uuid4().hex
        
        # Save with the generated key
        serializer.save(
            user=self.request.user,
            key=random_key
        )
    
    @action(detail=False, methods=['post'])
    def regenerate(self, request):
        """Regenerate an API key."""
        key_id = request.data.get('key_id')
        
        try:
            api_key = APIKey.objects.get(id=key_id, user=request.user)
            
            # Generate a new key
            new_key = uuid.uuid4().hex + uuid.uuid4().hex
            api_key.key = new_key
            api_key.save()
            
            serializer = self.get_serializer(api_key)
            return Response(serializer.data)
            
        except APIKey.DoesNotExist:
            return Response(
                {"error": "API key not found"},
                status=status.HTTP_404_NOT_FOUND
            )


class APIKeyAuthentication(permissions.BasePermission):
    """Permission class to authenticate using API key."""
    
    def has_permission(self, request, view):
        """Check if the request has a valid API key."""
        api_key = request.META.get('HTTP_X_API_KEY') or request.query_params.get('api_key')
        
        if not api_key:
            return False
        
        try:
            # Look up the API key
            key_obj = APIKey.objects.get(key=api_key, is_active=True)
            
            # Update usage statistics
            key_obj.last_used = timezone.now()
            key_obj.save()
            
            # Update profile statistics
            profile = key_obj.user.profile
            profile.api_requests_count += 1
            profile.last_api_request = timezone.now()
            profile.save()
            
            # Set the authenticated user
            request.user = key_obj.user
            return True
            
        except APIKey.DoesNotExist:
            return False
