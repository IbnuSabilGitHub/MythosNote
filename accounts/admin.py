from django.contrib import admin

from .models import UserProfile, UserUsage


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Expose verification state for operational support."""

    list_display = ("user", "email_verified", "created_at", "updated_at")
    list_filter = ("email_verified",)
    search_fields = ("user__username", "user__email")


@admin.register(UserUsage)
class UserUsageAdmin(admin.ModelAdmin):
    """Inspect rate-limit counters and future daily AI usage quotas."""

    list_display = (
        "user",
        "identifier",
        "date",
        "prompt_count",
        "generate_count",
        "failed_login_count",
    )
    list_filter = ("date",)
    search_fields = ("identifier", "user__username", "user__email")
