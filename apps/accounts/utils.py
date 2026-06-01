"""Utilitas auth bersama untuk akun, login, dan alur email."""

from datetime import timedelta
from typing import Any
import logging

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator, default_token_generator
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.db.models import F
from django.http import HttpRequest
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.html import strip_tags
from django.utils.http import urlsafe_base64_encode
import django_rq

from .models import UserProfile, UserUsage


logger = logging.getLogger(__name__)


LOGIN_RATE_LIMIT_ATTEMPTS = 5
LOGIN_RATE_LIMIT_WINDOW = timedelta(minutes=15)
VERIFICATION_RESEND_COOLDOWN = timedelta(minutes=5)
GOOGLE_OAUTH_RATE_LIMIT_ATTEMPTS = 10
GOOGLE_OAUTH_RATE_LIMIT_WINDOW = 300
PASSWORD_RESET_EMAIL_COOLDOWN = 300
PASSWORD_RESET_RATE_LIMIT_ATTEMPTS = 5
PASSWORD_RESET_RATE_LIMIT_WINDOW = 300


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """Token batal saat status verifikasi email berubah."""

    def _make_hash_value(self, user: Any, timestamp: int) -> str:
        profile, _ = UserProfile.objects.get_or_create(user=user)
        verified = profile.email_verified
        last_sent = profile.last_verification_email_sent_at
        return f"{user.pk}{user.password}{timestamp}{verified}{last_sent}{user.email}"


email_verification_token_generator = EmailVerificationTokenGenerator()


def normalize_identifier(identifier: str | None) -> str:
    """Normalisasi identifier login agar bucket rate-limit konsisten."""

    return (identifier or "").strip().lower()


def get_client_ip(request: HttpRequest) -> str | None:
    """Ambil IP klien terbaik dengan memperhatikan proxy.

    X-Forwarded-For hanya dipercaya jika REMOTE_ADDR berasal dari
    daftar proxy terpercaya (settings.TRUSTED_PROXY_IPS).  Tanpa
    konfigurasi tersebut, header XFF diabaikan untuk mencegah spoofing.
    """
    import ipaddress

    remote_addr = request.META.get("REMOTE_ADDR")
    trusted_proxies = getattr(settings, "TRUSTED_PROXY_IPS", [])

    if trusted_proxies and remote_addr:
        try:
            remote_ip = ipaddress.ip_address(remote_addr)
            is_trusted = any(
                remote_ip in ipaddress.ip_network(cidr, strict=False)
                for cidr in trusted_proxies
            )
        except ValueError:
            is_trusted = False

        if is_trusted:
            forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
            if forwarded_for:
                # Ambil IP paling kiri (client asli)
                return forwarded_for.split(",", 1)[0].strip()

    return remote_addr


def increment_cache_counter(cache_key: str, timeout: int) -> int:
    """Increment with TTL while keeping first-write behavior atomic."""

    if cache.add(cache_key, 1, timeout):
        return 1
    return cache.incr(cache_key)


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
    attempts = increment_cache_counter(cache_key, GOOGLE_OAUTH_RATE_LIMIT_WINDOW)
    return attempts > GOOGLE_OAUTH_RATE_LIMIT_ATTEMPTS


def is_password_reset_rate_limited(request: HttpRequest) -> bool:
    """Batasi volume request reset password per IP."""

    ip_address = get_client_ip(request) or "unknown"
    cache_key = f"password-reset-rate:{ip_address}"
    attempts = increment_cache_counter(cache_key, PASSWORD_RESET_RATE_LIMIT_WINDOW)
    return attempts > PASSWORD_RESET_RATE_LIMIT_ATTEMPTS


def can_send_password_reset_email(user: Any) -> bool:
    """Batasi kirim email reset per akun tanpa bocorkan status."""

    return cache.get(f"password-reset-cooldown:{user.pk}") is None


def get_login_usage(request: HttpRequest, identifier: str) -> UserUsage:
    """Ambil atau buat usage login hari ini untuk identifier/IP."""

    normalized = normalize_identifier(identifier)
    today = timezone.localdate()
    user = None
    if normalized:
        user = get_user_model().objects.filter(email__iexact=normalized).first()

    ip_address = get_client_ip(request)
    usage_identifier = f"{normalized}|{ip_address or 'unknown'}"

    usage, _ = UserUsage.objects.get_or_create(
        user=user,
        identifier=usage_identifier,
        date=today,
        defaults={"ip_address": ip_address},
    )
    return usage


def is_login_rate_limited(usage: UserUsage) -> bool:
    """Cek apakah percobaan gagal masih dalam jendela lock."""

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
    """Tambah hitungan gagal untuk jendela lock saat ini."""

    with transaction.atomic():
        locked_usage = UserUsage.objects.select_for_update().get(pk=usage.pk)
        now = timezone.now()
        if not locked_usage.failed_login_window_started_at:
            locked_usage.failed_login_window_started_at = now
            locked_usage.failed_login_count = 0
            locked_usage.save(update_fields=["failed_login_count", "failed_login_window_started_at"])

        UserUsage.objects.filter(pk=locked_usage.pk).update(
            failed_login_count=F("failed_login_count") + 1,
            last_failed_login_at=now,
        )


def clear_failed_login_tracking(usage: UserUsage) -> None:
    """Reset hitungan gagal setelah auth sukses."""

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
    """Kembalikan status verifikasi sambil toleran user lama tanpa profil."""

    if not user.is_authenticated:
        return False
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile.email_verified


def build_absolute_auth_url(request: HttpRequest, route_name: str, **kwargs: Any) -> str:
    """Bangun URL absolut untuk verifikasi email dan reset."""

    return request.build_absolute_uri(reverse(route_name, kwargs=kwargs))


def _send_mail_job(
    subject: str,
    message: str,
    recipient_list: list[str],
    from_email: str,
    html_message: str | None = None,
) -> None:
    email = EmailMultiAlternatives(
        subject=subject,
        body=message,
        from_email=from_email,
        to=recipient_list,
    )
    if html_message:
        email.attach_alternative(html_message, "text/html")
    email.send(fail_silently=False)


def _dispatch_email(
    subject: str,
    message: str,
    recipient_list: list[str],
    html_message: str | None = None,
) -> None:
    if settings.EMAIL_ASYNC:
        try:
            queue = django_rq.get_queue("default")
            queue.enqueue(
                _send_mail_job,
                subject,
                message,
                recipient_list,
                settings.DEFAULT_FROM_EMAIL,
                html_message,
            )
            return
        except Exception as exc:
            logger.warning(
                "Async email enqueue failed; falling back to sync.",
                exc_info=exc,
            )
    _send_mail_job(subject, message, recipient_list, settings.DEFAULT_FROM_EMAIL, html_message)


def _is_console_email_backend() -> bool:
    return settings.EMAIL_BACKEND == "django.core.mail.backends.console.EmailBackend"


def send_verification_email(request: HttpRequest, user: Any) -> None:
    """Kirim link verifikasi bertanda lewat backend email Django."""

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
    text_message = (
        "Halo,\n\n"
        "Klik link berikut untuk memverifikasi email MythosNote Anda:\n"
        f"{verify_url}\n\n"
        "Jika Anda tidak membuat akun MythosNote, abaikan email ini."
    )
    html_message = None
    if not _is_console_email_backend():
        html_message = render_to_string(
            "auth/emails/verification_email.html",
            {
                "verification_url": verify_url,
                "user_email": user.email,
            },
        )
    _dispatch_email(
        "Verifikasi email MythosNote",
        text_message,
        [user.email],
        html_message=html_message,
    )


def send_password_reset_email(request: HttpRequest, user: Any) -> None:
    """Kirim link reset password dengan token bawaan Django."""

    cache.set(f"password-reset-cooldown:{user.pk}", True, PASSWORD_RESET_EMAIL_COOLDOWN)

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    reset_url = build_absolute_auth_url(
        request,
        "password_reset_confirm",
        uidb64=uid,
        token=token,
    )
    html_message = render_to_string(
        "auth/emails/password_reset_email.html",
        {
            "reset_url": reset_url,
            "user_email": user.email,
        },
    )
    text_message = (
        "Halo,\n\n"
        "Klik link berikut untuk membuat password baru:\n"
        f"{reset_url}\n\n"
        "Jika Anda tidak meminta reset password, abaikan email ini."
    )
    _dispatch_email(
        "Reset password MythosNote",
        text_message if not html_message else strip_tags(html_message),
        [user.email],
        html_message=html_message,
    )


def verify_google_credential(credential: str) -> dict[str, str | bool]:
    """Validasi credential Google lewat endpoint tokeninfo."""

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
