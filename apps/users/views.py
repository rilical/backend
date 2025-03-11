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
        """Filter queryset based on permissions."""
        user = self.request.user
        if user.is_staff:
            return User.objects.all()
        return User.objects.filter(id=user.id)
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user's data."""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


class APIKeyViewSet(viewsets.ModelViewSet):
    """API endpoint for managing API keys."""
    serializer_class = APIKeySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter to only show user's own API keys."""
        return APIKey.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        """Create new API key for the user."""
        # Generate a secure API key
        api_key = base64.b64encode(uuid.uuid4().bytes).decode('utf-8')
        
        # Create a key prefix for identification
        prefix = api_key[:8]
        
        # Hash the API key for storage
        hashed_key = hashlib.sha256(api_key.encode('utf-8')).hexdigest()
        
        serializer.save(
            user=self.request.user,
            key_prefix=prefix,
            hashed_key=hashed_key
        )
        
        # Return the API key to the user (only time it will be visible)
        serializer.instance.raw_key = api_key
    
    @action(detail=False, methods=['post'])
    def regenerate(self, request):
        """Regenerate API key for a user."""
        try:
            # Find the user's current API key
            api_key_obj = APIKey.objects.get(
                user=request.user,
                key_prefix=request.data.get('key_prefix')
            )
            
            # Generate a new API key
            new_api_key = base64.b64encode(uuid.uuid4().bytes).decode('utf-8')
            new_prefix = new_api_key[:8]
            new_hashed_key = hashlib.sha256(new_api_key.encode('utf-8')).hexdigest()
            
            # Update the object
            api_key_obj.key_prefix = new_prefix
            api_key_obj.hashed_key = new_hashed_key
            api_key_obj.created_at = timezone.now()
            api_key_obj.save()
            
            # Return the new key to the user
            return Response({
                'key_prefix': new_prefix,
                'api_key': new_api_key,
                'created_at': api_key_obj.created_at
            })
            
        except APIKey.DoesNotExist:
            return Response(
                {'error': 'API key not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class APIKeyAuthentication(permissions.BasePermission):
    """Permission class for API key authentication."""
    def has_permission(self, request, view):
        api_key = request.META.get('HTTP_X_API_KEY', '')
        if not api_key:
            return False
            
        prefix = api_key[:8]
        hashed_key = hashlib.sha256(api_key.encode('utf-8')).hexdigest()
        
        try:
            key_obj = APIKey.objects.get(key_prefix=prefix, hashed_key=hashed_key)
            request.user = key_obj.user
            return True
        except APIKey.DoesNotExist:
            return False
