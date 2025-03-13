import uuid
from django.db import models
from django.utils import timezone

class APIKey(models.Model):
    """
    API key model for access control without user authentication.
    
    API keys are assigned to clients/partners and provide:
    1. Increased rate limits
    2. Access to premium features
    3. Usage tracking
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=100, help_text="Name of client/partner")
    email = models.EmailField(blank=True, null=True, help_text="Contact email")
    
    # Tier options
    TIER_REGISTERED = 'registered'
    TIER_PREMIUM = 'premium'
    TIER_ENTERPRISE = 'enterprise'
    
    TIER_CHOICES = [
        (TIER_REGISTERED, 'Registered'),
        (TIER_PREMIUM, 'Premium'),
        (TIER_ENTERPRISE, 'Enterprise'),
    ]
    
    tier = models.CharField(
        max_length=20, 
        choices=TIER_CHOICES,
        default=TIER_REGISTERED,
        help_text="Access tier that determines rate limits and feature access"
    )
    
    # Constraints
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    
    # Rate limits
    rate_limit = models.IntegerField(
        default=300,
        help_text="Requests per minute allowed"
    )
    
    # Track usage
    total_requests = models.BigIntegerField(default=0)
    
    class Meta:
        verbose_name = "API Key"
        verbose_name_plural = "API Keys"
    
    def __str__(self):
        return f"{self.name} ({self.tier})"
    
    def is_valid(self):
        """Check if the API key is valid and active"""
        if not self.is_active:
            return False
            
        if self.revoked_at is not None:
            return False
            
        if self.expires_at is not None and self.expires_at < timezone.now():
            return False
            
        return True
    
    def record_usage(self):
        """Record that the API key was used"""
        self.last_used_at = timezone.now()
        self.total_requests += 1
        # Use update to avoid race conditions
        APIKey.objects.filter(pk=self.pk).update(
            last_used_at=self.last_used_at,
            total_requests=models.F('total_requests') + 1
        )
    
    @classmethod
    def generate_key(cls):
        """Generate a new API key"""
        return uuid.uuid4().hex

class APIKeyUsageLog(models.Model):
    """
    Log of API key usage for analytics and billing.
    """
    api_key = models.ForeignKey(
        APIKey, 
        on_delete=models.CASCADE,
        related_name='usage_logs'
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    endpoint = models.CharField(max_length=255)
    http_method = models.CharField(max_length=10)
    response_time_ms = models.IntegerField()
    status_code = models.IntegerField()
    ip_address = models.GenericIPAddressField()
    user_agent = models.CharField(max_length=255, blank=True)
    
    class Meta:
        verbose_name = "API Key Usage Log"
        verbose_name_plural = "API Key Usage Logs"
        indexes = [
            models.Index(fields=['api_key', 'timestamp']),
            models.Index(fields=['endpoint']),
        ] 