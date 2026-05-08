"""Shared authentication utilities for account, login, and email workflows."""

from datetime import timedelta
from typing import Any
import logging

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator, default_token_generator
from django.core.cache import cache
from django.core.mail import send_mail
from django.http import HttpRequest
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
import django_rq

from .models import UserProfile, UserUsage


logger = logging.getLogger(__name__)


LOGIN_RATE_LIMIT_ATTEMPTS = 5
LOGIN_RATE_LIMIT_WINDOW = timedelta(minutes=15)
VERIFICATION_RESEND_COOLDOWN = timedelta(minutes=5)
GOOGLE_OAUTH_RATE_LIMIT_ATTEMPTS = 10
GOOGLE_OAUTH_RATE_LIMIT_WINDOW = 300


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """Token invalidates after email verification state changes."""

    def _make_hash_value(self, user: Any, timestamp: int) -> str:
        profile, _ = UserProfile.objects.get_or_create(user=user)
        verified = profile.email_verified
        last_sent = profile.last_verification_email_sent_at
        return f"{user.pk}{user.password}{timestamp}{verified}{last_sent}{user.email}"


email_verification_token_generator = EmailVerificationTokenGenerator()


def normalize_identifier(identifier: str | None) -> str:
    """Normalize login identifiers so rate-limit buckets stay consistent."""

    return (identifier or "").strip().lower()


def get_client_ip(request: HttpRequest) -> str | None:
    """Return the best-effort client IP while staying proxy-aware."""

    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.META.get("REMOTE_ADDR")


def get_verification_resend_wait_seconds(user: Any) -> int:
    profile, _ = UserProfile.objects.get_or_create(user=user)
    if not profile.last_verification_email_sent_at:
        return 0

    retry_at = profile.last_verification_email_sent_at + VERIFICATION_RESEND_COOLDOWN
    remaining = retry_at - timezone.now()
    return max(0, int(remaining.total_seconds()))


def can_send_verification_email(user: Any) -> bool:
    return get_verification_resend_wait_seconds(user) == 0


def is_google_oauth_rate_limited(request: HttpRequest) -> bool:
    ip_address = get_client_ip(request) or "unknown"
    cache_key = f"google-oauth-rate:{ip_address}"
    attempts = cache.get(cache_key, 0)
    if attempts >= GOOGLE_OAUTH_RATE_LIMIT_ATTEMPTS:
        return True
    cache.set(cache_key, attempts + 1, GOOGLE_OAUTH_RATE_LIMIT_WINDOW)
    return False


def get_login_usage(request: HttpRequest, identifier: str) -> UserUsage:
    """Fetch or create today's login usage row for an identifier/IP pair."""

    normalized = normalize_identifier(identifier)
    today = timezone.localdate()
    user = None
    if normalized:
        query = {"email__iexact": normalized} if "@" in normalized else {"username__iexact": normalized}
        user = get_user_model().objects.filter(**query).first()

    usage, _ = UserUsage.objects.get_or_create(
        user=user,
        identifier=normalized,
        date=today,
        defaults={"ip_address": get_client_ip(request)},
    )
    return usage


def is_login_rate_limited(usage: UserUsage) -> bool:
    """Check whether failed login attempts are still inside the lock window."""

    if not usage.failed_login_window_started_at:
        return False

    window_expires_at = usage.failed_login_window_started_at + LOGIN_RATE_LIMIT_WINDOW
    if timezone.now() >= window_expires_at:
        usage.failed_login_count = 0
        usage.failed_login_window_started_at = None
        usage.last_failed_login_at = None
        usage.save(
            update_fields=[
                "failed_login_count",
                "failed_login_window_started_at",
                "last_failed_login_at",
            ]
        )
        return False

    return usage.failed_login_count >= LOGIN_RATE_LIMIT_ATTEMPTS


def record_failed_login(usage: UserUsage) -> None:
    """Increment failed login attempts for the current lock window."""

    now = timezone.now()
    if not usage.failed_login_window_started_at:
        usage.failed_login_window_started_at = now
        usage.failed_login_count = 0

    usage.failed_login_count += 1
    usage.last_failed_login_at = now
    usage.save(
        update_fields=[
            "failed_login_count",
            "failed_login_window_started_at",
            "last_failed_login_at",
        ]
    )


def clear_failed_login_tracking(usage: UserUsage) -> None:
    """Clear failed login counters after a successful authentication."""

    usage.failed_login_count = 0
    usage.failed_login_window_started_at = None
    usage.last_failed_login_at = None
    usage.save(
        update_fields=[
            "failed_login_count",
            "failed_login_window_started_at",
            "last_failed_login_at",
        ]
    )


def is_email_verified(user: Any) -> bool:
    """Return verification state while tolerating legacy users without profile rows."""

    if not user.is_authenticated:
        return False
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile.email_verified


def build_absolute_auth_url(request: HttpRequest, route_name: str, **kwargs: Any) -> str:
    """Build absolute URLs used in email verification and reset messages."""

    return request.build_absolute_uri(reverse(route_name, kwargs=kwargs))


def _send_mail_job(subject: str, message: str, recipient_list: list[str], from_email: str) -> None:
    send_mail(
        subject,
        message,
        from_email,
        recipient_list,
        fail_silently=False,
    )


def _dispatch_email(subject: str, message: str, recipient_list: list[str]) -> None:
    if settings.EMAIL_ASYNC:
        try:
            queue = django_rq.get_queue("default")
            queue.enqueue(
                _send_mail_job,
                subject,
                message,
                recipient_list,
                settings.DEFAULT_FROM_EMAIL,
            )
            return
        except Exception as exc:
            logger.warning(
                "Async email enqueue failed; falling back to sync.",
                exc_info=exc,
            )

    _send_mail_job(subject, message, recipient_list, settings.DEFAULT_FROM_EMAIL)


def send_verification_email(request: HttpRequest, user: Any) -> None:
    """Send a signed email verification link via Django's configured email backend."""

    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.last_verification_email_sent_at = timezone.now()
    profile.save(update_fields=["last_verification_email_sent_at", "updated_at"])

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = email_verification_token_generator.make_token(user)
    verify_url = build_absolute_auth_url(
        request,
        "verify_email",
        uidb64=uid,
        token=token,
    )
    _dispatch_email(
        "Verifikasi email MythosNote",
        (
            "Halo,\n\n"
            "Klik link berikut untuk memverifikasi email MythosNote Anda:\n"
            f"{verify_url}\n\n"
            "Jika Anda tidak membuat akun MythosNote, abaikan email ini."
        ),
        [user.email],
    )


def send_password_reset_email(request: HttpRequest, user: Any) -> None:
    """Send a password reset link using Django's default signed token."""

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    reset_url = build_absolute_auth_url(
        request,
        "password_reset_confirm",
        uidb64=uid,
        token=token,
    )
    _dispatch_email(
        "Reset password MythosNote",
        (
            "Halo,\n\n"
            "Klik link berikut untuk membuat password baru:\n"
            f"{reset_url}\n\n"
            "Jika Anda tidak meminta reset password, abaikan email ini."
        ),
        [user.email],
    )


def verify_google_credential(credential: str) -> dict[str, str | bool]:
    """Validate a Google Identity Services credential through Google's tokeninfo endpoint."""

    response = requests.get(
        "https://oauth2.googleapis.com/tokeninfo",
        params={"id_token": credential},
        timeout=8,
    )
    response.raise_for_status()
    payload = response.json()

    if payload.get("aud") != settings.GOOGLE_OAUTH_CLIENT_ID:
        raise ValueError("Token Google tidak sesuai client aplikasi.")
    if not payload.get("email"):
        raise ValueError("Token Google tidak berisi email.")

    return {
        "email": payload["email"].lower(),
        "name": payload.get("name", ""),
        "email_verified": payload.get("email_verified") in (True, "true", "True"),
    }
