"""Context processor template untuk setelan auth aman."""

from typing import Any

from django.conf import settings
from django.http import HttpRequest

from .models import UserProfile


def auth_settings(request: HttpRequest) -> dict[str, Any]:
    """Sediakan setelan auth publik aman untuk UI template."""

    email_verified = False
    if request.user.is_authenticated:
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        email_verified = profile.email_verified

    return {
        "GOOGLE_OAUTH_CLIENT_ID": settings.GOOGLE_OAUTH_CLIENT_ID,
        "AUTH_EMAIL_VERIFIED": email_verified,
    }
