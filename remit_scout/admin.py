from django.contrib import admin
from remit_scout.models import APIKey, APIKeyUsageLog

@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ('name', 'key_preview', 'tier', 'is_active', 'created_at', 'expires_at', 'total_requests')
    list_filter = ('tier', 'is_active')
    search_fields = ('name', 'email', 'key')
    readonly_fields = ('id', 'created_at', 'last_used_at', 'total_requests')
    fieldsets = (
        (None, {
            'fields': ('id', 'key', 'name', 'email', 'tier')
        }),
        ('Status', {
            'fields': ('is_active', 'created_at', 'expires_at', 'revoked_at', 'last_used_at')
        }),
        ('Usage', {
            'fields': ('rate_limit', 'total_requests')
        }),
    )
    
    def key_preview(self, obj):
        """Show first 8 characters of API key for reference"""
        return f"{obj.key[:8]}..." if obj.key else ""
    key_preview.short_description = "API Key (preview)"

@admin.register(APIKeyUsageLog)
class APIKeyUsageLogAdmin(admin.ModelAdmin):
    list_display = ('api_key', 'endpoint', 'http_method', 'status_code', 'response_time_ms', 'timestamp')
    list_filter = ('http_method', 'status_code', 'timestamp')
    search_fields = ('endpoint', 'ip_address', 'user_agent')
    readonly_fields = ('api_key', 'timestamp', 'endpoint', 'http_method', 'response_time_ms', 'status_code', 'ip_address', 'user_agent')
    
    def has_add_permission(self, request):
        """Disable manual creation of usage logs"""
        return False
        
    def has_change_permission(self, request, obj=None):
        """Disable editing of usage logs"""
        return False 