"""Signal handlers for keeping authentication state in sync."""

from typing import Any

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserProfile


@receiver(post_save, sender=get_user_model())
def ensure_user_profile(sender: Any, instance: Any, created: bool, **kwargs: Any) -> None:
    """Ensure every user has profile state for email verification gates."""

    if created:
        UserProfile.objects.get_or_create(user=instance)
