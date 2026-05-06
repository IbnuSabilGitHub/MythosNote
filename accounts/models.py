from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    """Small auth profile kept separate from Django's built-in user table."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile<{self.user_id}>"


class UserUsage(models.Model):
    """Per-day usage tracker prepared for login limits and future AI quotas."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="usage_records",
    )
    identifier = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    date = models.DateField()
    prompt_count = models.PositiveIntegerField(default=0)
    generate_count = models.PositiveIntegerField(default=0)
    failed_login_count = models.PositiveIntegerField(default=0)
    failed_login_window_started_at = models.DateTimeField(null=True, blank=True)
    last_failed_login_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "identifier", "date"],
                name="unique_user_usage_per_identifier_day",
            ),
        ]
        indexes = [
            models.Index(fields=["date", "identifier"]),
            models.Index(fields=["date", "user"]),
        ]

    def __str__(self):
        owner = self.user_id or self.identifier or "anonymous"
        return f"Usage<{owner}:{self.date}>"
