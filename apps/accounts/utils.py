"""Utilitas auth bersama untuk akun, login, dan alur email."""

from datetime import timedelta
from typing import Any
import logging
import hashlib

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
MAX_CONCURRENT_REQUESTS = 5
CONCURRENT_REQUEST_WINDOW = timedelta(seconds=10)

# Prioritas TINGGI: Sliding window & token bucket settings
SLIDING_WINDOW_SIZE = timedelta(minutes=1)  # Window untuk rate limiting per-menit
SLIDING_WINDOW_MAX_REQUESTS = 10  # Max request per menit
TOKEN_BUCKET_CAPACITY = 20  # Kapasitas maksimum token
TOKEN_BUCKET_REFILL_RATE = 2  # Token per detik
TOKEN_BUCKET_KEY_PREFIX = "token_bucket"


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


def generate_device_fingerprint(request: HttpRequest) -> str:
    """Generate device fingerprint dari header HTTP yang konsisten.
    
    Menggabungkan User-Agent, Accept-Language, dan Accept-Encoding
    untuk membuat identifikasi perangkat yang lebih sulit diakali.
    """
    user_agent = request.META.get("HTTP_USER_AGENT", "")
    accept_language = request.META.get("HTTP_ACCEPT_LANGUAGE", "")
    accept_encoding = request.META.get("HTTP_ACCEPT_ENCODING", "")
    
    fingerprint_data = f"{user_agent}|{accept_language}|{accept_encoding}"
    return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:64]


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


def get_api_usage(user: Any, request: HttpRequest) -> UserUsage:
    """Ambil atau buat tracking pemakaian API untuk user/IP hari ini."""

    today = timezone.localdate()
    ip_address = get_client_ip(request)
    device_fingerprint = generate_device_fingerprint(request)
    identifier = user.email if hasattr(user, 'email') else f"anon|{ip_address or 'unknown'}"
    
    usage, created = UserUsage.objects.get_or_create(
        user=user if user.is_authenticated else None,
        identifier=identifier,
        date=today,
        defaults={
            "ip_address": ip_address,
            "device_fingerprint": device_fingerprint,
        },
    )
    
    # Update device fingerprint jika berubah (misal browser update)
    if not created and usage.device_fingerprint != device_fingerprint:
        usage.device_fingerprint = device_fingerprint
        usage.save(update_fields=["device_fingerprint"])
    
    return usage


def check_concurrent_request_limit(user: Any, request: HttpRequest) -> bool:
    """Periksa apakah pengguna melebihi batas permintaan bersamaan.
    
    Returns True jika masih dalam batas, False jika sudah melebihi.
    Menggunakan cache atomik untuk tracking concurrent requests.
    """
    if not user.is_authenticated:
        return True
    
    cache_key = f"concurrent_requests:{user.pk}"
    now = timezone.now()
    window_seconds = int(CONCURRENT_REQUEST_WINDOW.total_seconds())
    
    # Gunakan Redis/hash map untuk tracking concurrent requests
    # Dengan cleanup otomatis berdasarkan waktu
    current_count = cache.get(cache_key, 0)
    
    if current_count >= MAX_CONCURRENT_REQUESTS:
        return False
    
    # Increment counter dengan TTL pendek
    cache.set(cache_key, current_count + 1, window_seconds)
    return True


def release_concurrent_request(user: Any, request: HttpRequest) -> None:
    """Release slot concurrent request setelah selesai diproses."""
    if not user.is_authenticated:
        return
    
    cache_key = f"concurrent_requests:{user.pk}"
    current_count = cache.get(cache_key, 0)
    
    if current_count > 0:
        cache.set(cache_key, current_count - 1, int(CONCURRENT_REQUEST_WINDOW.total_seconds()))


def check_sliding_window_rate_limit(user: Any, request: HttpRequest) -> bool:
    """Periksa rate limiting dengan sliding window log.
    
    Menggunakan Redis sorted set untuk tracking timestamp request dalam window.
    Ini memberikan akurasi lebih tinggi dibanding fixed window counter.
    
    Returns True jika masih dalam batas, False jika sudah melebihi.
    """
    if not user.is_authenticated:
        return True
    
    cache_key = f"sliding_window:{user.pk}"
    now = timezone.now().timestamp()
    window_start = now - SLIDING_WINDOW_SIZE.total_seconds()
    
    # Hapus request lama di luar window (atomik dengan Redis ZREMRANGEBYSCORE)
    cache.zremrangebyscore(cache_key, '-inf', window_start)
    
    # Hitung jumlah request dalam window
    current_count = cache.zcard(cache_key)
    
    if current_count >= SLIDING_WINDOW_MAX_REQUESTS:
        return False
    
    # Tambahkan request baru dengan timestamp sebagai score
    # Gunakan unique member untuk menghindari duplikasi
    member = f"{now}:{id(request)}"
    cache.zadd(cache_key, {member: now})
    
    # Set TTL untuk cleanup otomatis
    cache.expire(cache_key, int(SLIDING_WINDOW_SIZE.total_seconds() * 2))
    
    return True


def check_token_bucket(user: Any, request: HttpRequest, tokens_required: int = 1) -> bool:
    """Periksa dan konsumsi token dari token bucket.
    
    Algoritma token bucket memberikan fleksibilitas untuk burst traffic
    sambil menjaga rata-rata rate dalam batas yang ditentukan.
    
    Args:
        user: User object
        request: Request object
        tokens_required: Jumlah token yang dibutuhkan (default 1)
    
    Returns:
        True jika token tersedia dan berhasil dikonsumsi, False jika tidak
    """
    if not user.is_authenticated:
        return True
    
    cache_key = f"{TOKEN_BUCKET_KEY_PREFIX}:{user.pk}"
    now = timezone.now().timestamp()
    
    # Ambil state bucket saat ini
    bucket_data = cache.get(cache_key)
    
    if bucket_data is None:
        # Initialize bucket dengan kapasitas penuh
        tokens = TOKEN_BUCKET_CAPACITY
        last_update = now
    else:
        tokens, last_update = bucket_data
        
        # Refill token berdasarkan waktu yang berlalu
        time_passed = now - last_update
        tokens_to_add = time_passed * TOKEN_BUCKET_REFILL_RATE
        tokens = min(TOKEN_BUCKET_CAPACITY, tokens + tokens_to_add)
    
    # Cek apakah ada cukup token
    if tokens < tokens_required:
        return False
    
    # Konsumsi token
    tokens -= tokens_required
    
    # Simpan state bucket yang diupdate
    cache.set(cache_key, (tokens, now), timeout=3600)  # TTL 1 jam
    
    return True


def get_remaining_tokens(user: Any) -> dict:
    """Dapatkan informasi sisa token dan quota untuk user.
    
    Returns dict dengan informasi:
    - remaining_tokens: Token tersisa di bucket
    - max_tokens: Kapasitas maksimum bucket
    - refill_rate: Kecepatan refill token per detik
    - requests_in_window: Jumlah request dalam sliding window saat ini
    - max_requests_per_minute: Batas request per menit
    """
    if not user.is_authenticated:
        return {
            "remaining_tokens": TOKEN_BUCKET_CAPACITY,
            "max_tokens": TOKEN_BUCKET_CAPACITY,
            "refill_rate": TOKEN_BUCKET_REFILL_RATE,
            "requests_in_window": 0,
            "max_requests_per_minute": SLIDING_WINDOW_MAX_REQUESTS,
        }
    
    # Get token bucket info
    cache_key = f"{TOKEN_BUCKET_KEY_PREFIX}:{user.pk}"
    bucket_data = cache.get(cache_key)
    
    if bucket_data is None:
        tokens = TOKEN_BUCKET_CAPACITY
    else:
        tokens, last_update = bucket_data
        time_passed = timezone.now().timestamp() - last_update
        tokens_to_add = time_passed * TOKEN_BUCKET_REFILL_RATE
        tokens = min(TOKEN_BUCKET_CAPACITY, tokens + tokens_to_add)
    
    # Get sliding window info
    window_key = f"sliding_window:{user.pk}"
    now = timezone.now().timestamp()
    window_start = now - SLIDING_WINDOW_SIZE.total_seconds()
    
    # Cleanup dan hitung
    cache.zremrangebyscore(window_key, '-inf', window_start)
    requests_in_window = cache.zcard(window_key)
    
    return {
        "remaining_tokens": int(tokens),
        "max_tokens": TOKEN_BUCKET_CAPACITY,
        "refill_rate": TOKEN_BUCKET_REFILL_RATE,
        "requests_in_window": requests_in_window,
        "max_requests_per_minute": SLIDING_WINDOW_MAX_REQUESTS,
    }


def check_and_increment_prompt(user: Any, request: HttpRequest) -> bool:
    """Periksa kuota chat harian dan inkremen jika masih tersedia.
    
    Menggunakan UPDATE atomic dengan kondisi WHERE untuk mencegah race condition.
    Juga memeriksa batas concurrent requests, sliding window, dan token bucket.
    
    Lapisan pertahanan (defense in depth):
    1. Concurrent request limit - Mencegah serangan paralel
    2. Sliding window rate limit - Mencegah spam per-menit
    3. Token bucket - Mengatur burst traffic dengan smooth rate limiting
    4. Daily quota - Batas harian total
    """
    # Layer 1: Cek concurrent request limit
    if not check_concurrent_request_limit(user, request):
        return False
    
    # Layer 2: Cek sliding window rate limit (per menit)
    if not check_sliding_window_rate_limit(user, request):
        release_concurrent_request(user, request)
        return False
    
    # Layer 3: Cek token bucket (burst control)
    if not check_token_bucket(user, request, tokens_required=1):
        release_concurrent_request(user, request)
        return False
    
    try:
        # Layer 4: Gunakan query UPDATE atomik dengan kondisi WHERE
        # Ini mencegah race condition karena database yang menangani locking
        with transaction.atomic():
            today = timezone.localdate()
            ip_address = get_client_ip(request)
            device_fingerprint = generate_device_fingerprint(request)
            identifier = user.email if hasattr(user, 'email') else f"anon|{ip_address or 'unknown'}"
            
            # Query atomik: increment hanya jika masih di bawah limit
            # Menggunakan F() expression dengan kondisi di filter
            updated = UserUsage.objects.filter(
                user=user if user.is_authenticated else None,
                identifier=identifier,
                date=today,
                prompt_count__lt=settings.AI_DAILY_PROMPT_LIMIT,
            ).update(
                prompt_count=F("prompt_count") + 1,
                last_request_at=timezone.now(),
                device_fingerprint=device_fingerprint,
            )
            
            if updated == 0:
                # Tidak ada baris yang di-update = quota sudah habis
                # Atau perlu create record baru
                usage, created = UserUsage.objects.get_or_create(
                    user=user if user.is_authenticated else None,
                    identifier=identifier,
                    date=today,
                    defaults={
                        "ip_address": ip_address,
                        "device_fingerprint": device_fingerprint,
                        "prompt_count": 1 if settings.AI_DAILY_PROMPT_LIMIT > 0 else 0,
                    },
                )
                
                if not created and usage.prompt_count >= settings.AI_DAILY_PROMPT_LIMIT:
                    return False
                
                # Jika baru dibuat dan limit > 0, berarti berhasil
                if created and settings.AI_DAILY_PROMPT_LIMIT > 0:
                    return True
                    
            return True
    finally:
        # Selalu release slot concurrent request
        release_concurrent_request(user, request)


def check_and_increment_generate(user: Any, request: HttpRequest) -> bool:
    """Periksa kuota generate harian dan inkremen jika masih tersedia.
    
    Menggunakan UPDATE atomic dengan kondisi WHERE untuk mencegah race condition.
    Juga memeriksa batas concurrent requests, sliding window, dan token bucket.
    
    Lapisan pertahanan (defense in depth):
    1. Concurrent request limit - Mencegah serangan paralel
    2. Sliding window rate limit - Mencegah spam per-menit
    3. Token bucket - Mengatur burst traffic dengan smooth rate limiting
    4. Daily quota - Batas harian total
    """
    # Layer 1: Cek concurrent request limit
    if not check_concurrent_request_limit(user, request):
        return False
    
    # Layer 2: Cek sliding window rate limit (per menit)
    if not check_sliding_window_rate_limit(user, request):
        release_concurrent_request(user, request)
        return False
    
    # Layer 3: Cek token bucket (burst control)
    if not check_token_bucket(user, request, tokens_required=2):  # Generate butuh 2 token
        release_concurrent_request(user, request)
        return False
    
    try:
        # Layer 4: Gunakan query UPDATE atomik dengan kondisi WHERE
        with transaction.atomic():
            today = timezone.localdate()
            ip_address = get_client_ip(request)
            device_fingerprint = generate_device_fingerprint(request)
            identifier = user.email if hasattr(user, 'email') else f"anon|{ip_address or 'unknown'}"
            
            updated = UserUsage.objects.filter(
                user=user if user.is_authenticated else None,
                identifier=identifier,
                date=today,
                generate_count__lt=settings.AI_DAILY_GENERATE_LIMIT,
            ).update(
                generate_count=F("generate_count") + 1,
                last_request_at=timezone.now(),
                device_fingerprint=device_fingerprint,
            )
            
            if updated == 0:
                usage, created = UserUsage.objects.get_or_create(
                    user=user if user.is_authenticated else None,
                    identifier=identifier,
                    date=today,
                    defaults={
                        "ip_address": ip_address,
                        "device_fingerprint": device_fingerprint,
                        "generate_count": 1 if settings.AI_DAILY_GENERATE_LIMIT > 0 else 0,
                    },
                )
                
                if not created and usage.generate_count >= settings.AI_DAILY_GENERATE_LIMIT:
                    return False
                
                if created and settings.AI_DAILY_GENERATE_LIMIT > 0:
                    return True
                    
            return True
    finally:
        release_concurrent_request(user, request)


def check_and_increment_upload(user: Any, request: HttpRequest) -> bool:
    """Periksa kuota upload harian dan inkremen jika masih tersedia.
    
    Menggunakan UPDATE atomic dengan kondisi WHERE untuk mencegah race condition.
    Juga memeriksa batas concurrent requests, sliding window, dan token bucket.
    
    Lapisan pertahanan (defense in depth):
    1. Concurrent request limit - Mencegah serangan paralel
    2. Sliding window rate limit - Mencegah spam per-menit
    3. Token bucket - Mengatur burst traffic dengan smooth rate limiting
    4. Daily quota - Batas harian total
    """
    # Layer 1: Cek concurrent request limit
    if not check_concurrent_request_limit(user, request):
        return False
    
    # Layer 2: Cek sliding window rate limit (per menit)
    if not check_sliding_window_rate_limit(user, request):
        release_concurrent_request(user, request)
        return False
    
    # Layer 3: Cek token bucket (burst control)
    if not check_token_bucket(user, request, tokens_required=3):  # Upload butuh 3 token
        release_concurrent_request(user, request)
        return False
    
    try:
        # Layer 4: Gunakan query UPDATE atomik dengan kondisi WHERE
        with transaction.atomic():
            today = timezone.localdate()
            ip_address = get_client_ip(request)
            device_fingerprint = generate_device_fingerprint(request)
            identifier = user.email if hasattr(user, 'email') else f"anon|{ip_address or 'unknown'}"
            
            updated = UserUsage.objects.filter(
                user=user if user.is_authenticated else None,
                identifier=identifier,
                date=today,
                upload_count__lt=settings.AI_DAILY_UPLOAD_LIMIT,
            ).update(
                upload_count=F("upload_count") + 1,
                last_request_at=timezone.now(),
                device_fingerprint=device_fingerprint,
            )
            
            if updated == 0:
                usage, created = UserUsage.objects.get_or_create(
                    user=user if user.is_authenticated else None,
                    identifier=identifier,
                    date=today,
                    defaults={
                        "ip_address": ip_address,
                        "device_fingerprint": device_fingerprint,
                        "upload_count": 1 if settings.AI_DAILY_UPLOAD_LIMIT > 0 else 0,
                    },
                )
                
                if not created and usage.upload_count >= settings.AI_DAILY_UPLOAD_LIMIT:
                    release_concurrent_request(user, request)
                    return False
                
                if created and settings.AI_DAILY_UPLOAD_LIMIT > 0:
                    return True
                    
            return True
    finally:
        release_concurrent_request(user, request)
