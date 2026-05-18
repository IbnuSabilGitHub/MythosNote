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


def navbar_config(request: HttpRequest) -> dict[str, Any]:
    """Sediakan konfigurasi navbar dinamis berdasarkan halaman."""
    path = request.path

    # Tentukan apakah navbar ditampilkan
    hide_patterns = ['signin', 'signup', 'forgot-password', 'password-reset', 'email-verification']
    show_navbar = not any(pattern in path for pattern in hide_patterns)

    # Tentukan tipe navbar berdasarkan path
    navbar_type = 'default'
    if '/project' in path:
        navbar_type = 'project'
    elif path == '/' or '/home' in path:
        navbar_type = 'home'

    return {
        'show_navbar': show_navbar,
        'navbar_type': navbar_type,
    }
