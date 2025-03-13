from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin
from django.contrib.auth.models import User

from .models import APIKey, UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = "User Profile"
    fk_name = "user"


class UserAdmin(DefaultUserAdmin):
    inlines = (UserProfileInline,)
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "get_api_requests",
    )

    def get_api_requests(self, obj):
        return obj.profile.api_requests_count

    get_api_requests.short_description = "API Requests"


class APIKeyAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "is_active", "created_at", "last_used")
    list_filter = ("is_active", "created_at")
    search_fields = ("name", "user__username")
    readonly_fields = ("key",)


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(APIKey, APIKeyAdmin)
