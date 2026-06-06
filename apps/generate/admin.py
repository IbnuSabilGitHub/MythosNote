from django.contrib import admin

from apps.generate.models import GenerateJob


@admin.register(GenerateJob)
class GenerateJobAdmin(admin.ModelAdmin):
    list_display = ("id", "workspace", "action", "status", "user", "created_at")
    list_filter = ("action", "status")
    search_fields = ("id", "title", "user__email")
    readonly_fields = ("created_at", "updated_at")
