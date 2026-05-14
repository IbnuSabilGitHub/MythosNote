"""Tampilan autentikasi untuk masuk, pendaftaran, dan verifikasi email."""

from typing import Any, Mapping

from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.tokens import default_token_generator
from django.db import IntegrityError, transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views.decorators.http import require_POST

from .decorators import guest_required
from .forms import ForgotPasswordForm, PasswordResetConfirmForm, SignInForm, SignUpForm
from .utils import (
    can_send_verification_email,
    can_send_password_reset_email,
    clear_failed_login_tracking,
    email_verification_token_generator,
    get_verification_resend_wait_seconds,
    get_login_usage,
    is_google_oauth_rate_limited,
    is_email_verified,
    is_login_rate_limited,
    is_password_reset_rate_limited,
    record_failed_login,
    send_password_reset_email,
    send_verification_email,
    verify_google_credential,
)


User = get_user_model()
PENDING_VERIFICATION_SESSION_KEY = "pending_verification_user_id"


def set_pending_verification_user(request: HttpRequest, user: Any) -> None:
    """Simpan target verifikasi di session untuk flow guest."""

    request.session[PENDING_VERIFICATION_SESSION_KEY] = user.pk


def clear_pending_verification_user(request: HttpRequest) -> None:
    """Hapus target verifikasi tersimpan dari session."""

    request.session.pop(PENDING_VERIFICATION_SESSION_KEY, None)


def get_pending_verification_user(request: HttpRequest) -> Any | None:
    """Ambil target verifikasi dari session guest bila ada."""

    user_id = request.session.get(PENDING_VERIFICATION_SESSION_KEY)
    if not user_id:
        return None
    return User.objects.filter(pk=user_id, is_active=False).first()


def get_verification_target_user(request: HttpRequest) -> Any | None:
    """Ambil user target resend/status tanpa menerima email mentah."""

    if request.user.is_authenticated:
        return request.user
    return get_pending_verification_user(request)


@guest_required
def sign_in(request: HttpRequest) -> HttpResponse:
    """Tangani login sesi dengan pembatasan percobaan gagal."""

    form = SignInForm(request=request, data=request.POST or None)
    if request.method == "POST":
        usage = get_login_usage(request, request.POST.get("email", ""))
        if is_login_rate_limited(usage):
            messages.error(request, "Terlalu banyak percobaan login. Coba lagi beberapa menit lagi.")
        elif form.is_valid():
            login(request, form.user)
            clear_failed_login_tracking(usage)
            clear_pending_verification_user(request)
            if not is_email_verified(form.user):
                return redirect("email_unverified")
            return redirect("home")
        elif form.inactive_user is not None:
            set_pending_verification_user(request, form.inactive_user)
            messages.error(request, "Akun belum aktif. Cek email verifikasi Anda atau kirim ulang dari halaman berikut.")
            return redirect("email_unverified")
        else:
            record_failed_login(usage)
            messages.error(request, "Email atau password salah.")

    return render(request, "signin.html", {"form": form, "hide_nav": True})


@guest_required
def sign_up(request: HttpRequest) -> HttpResponse:
    """Daftarkan akun lokal dan kirim email verifikasi pertama."""


    form = SignUpForm(data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save(commit=False)
        user.is_active = False
        user.save()
        user.profile.email_verified = False
        user.profile.save(update_fields=["email_verified", "updated_at"])
        send_verification_email(request, user)
        set_pending_verification_user(request, user)
        messages.success(request, "Akun berhasil dibuat. Cek email verifikasi Anda.")
        return redirect("email_unverified")

    if request.method == "POST" and not form.is_valid():
        for email_error in form.errors.get("email", []):
            messages.error(request, str(email_error))

    return render(request, "signup.html", {"form": form, "hide_nav": True})


@require_POST
@guest_required
def google_sign_in(request: HttpRequest) -> HttpResponse:
    """Login via Google dan buat akun lokal bila perlu."""

    if is_google_oauth_rate_limited(request):
        messages.error(request, "Terlalu banyak percobaan Google login. Coba lagi nanti.")
        return redirect("signin")

    credential = request.POST.get("credential", "")
    if not credential:
        messages.error(request, "Credential Google tidak ditemukan.")
        return redirect("signin")

    try:
        payload = verify_google_credential(credential)
    except Exception:
        messages.error(request, "Login Google gagal divalidasi.")
        return redirect("signin")

    try:
        user = get_or_create_google_user(payload)
    except IntegrityError:
        messages.error(request, "Email Google sudah terhubung ke akun lain.")
        return redirect("signin")

    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    if not is_email_verified(user):
        return redirect("email_unverified")
    return redirect("home")


def get_or_create_google_user(payload: Mapping[str, Any]) -> Any:
    """Buat user Django dari data profil Google tanpa tabel OAuth."""

    with transaction.atomic():
        user = User.objects.select_for_update().filter(email__iexact=payload["email"]).first()
        if user is None:
            user = User(username=None, email=payload["email"])
            user.set_unusable_password()
            user.save()
        if payload["email_verified"]:
            user.profile.email_verified = True
            user.profile.save(update_fields=["email_verified", "updated_at"])
        return user


def build_unique_username(email: str) -> str:
    """Buat username dari email dan hindari tabrakan."""

    seed = email.split("@", 1)[0].replace(".", "_")[:140] or "user"
    username = seed
    suffix = 1
    while User.objects.filter(username__iexact=username).exists():
        suffix += 1
        username = f"{seed}_{suffix}"
    return username


def email_unverified(request: HttpRequest) -> HttpResponse:
    """Tampilkan gerbang verifikasi.

    Support untuk user yang sudah login *dan* untuk flow dimana user belum
    terautentikasi (mis. setelah percobaan signin dengan akun unverified).
    """

    user = get_verification_target_user(request)
    if not user:
        messages.warning(request, "Sesi verifikasi tidak ditemukan. Silakan login lagi.")
        return redirect("signin")

    if is_email_verified(user):
        clear_pending_verification_user(request)
        return redirect("home")

    resend_wait_seconds = get_verification_resend_wait_seconds(user)
    return render(
        request,
        "auth/email_unverified.html",
        {"resend_wait_seconds": resend_wait_seconds, "hide_nav": not request.user.is_authenticated},
    )


@require_POST
def resend_verification(request: HttpRequest) -> HttpResponse:
    """Kirim ulang email verifikasi untuk user terikat session/login."""

    target_user = get_verification_target_user(request)
    if not target_user:
        messages.warning(request, "Sesi verifikasi tidak ditemukan. Silakan login lagi.")
        return redirect("signin")

    if is_email_verified(target_user):
        clear_pending_verification_user(request)
        return redirect("home")

    if not can_send_verification_email(target_user):
        messages.warning(request, "Tunggu sebentar sebelum kirim ulang link verifikasi.")
        return redirect("email_unverified")

    send_verification_email(request, target_user)
    messages.success(request, "Link verifikasi baru sudah dikirim.")
    return redirect("email_unverified")


def verify_email(request: HttpRequest, uidb64: str, token: str) -> HttpResponse:
    """Verifikasi email user dari URL token bertanda."""

    user = get_user_from_uid(uidb64)
    if user and email_verification_token_generator.check_token(user, token):
        user.is_active = True
        user.save(update_fields=["is_active"])
        user.profile.email_verified = True
        user.profile.save(update_fields=["email_verified", "updated_at"])
        if request.user.is_authenticated:
            logout(request)
        clear_pending_verification_user(request)
        messages.success(request, "Email berhasil diverifikasi. Silakan login.")
        return redirect("signin")

    messages.error(request, "Link verifikasi tidak valid atau sudah kedaluwarsa.")
    return render(request, "auth/email_verification_invalid.html")


def get_user_from_uid(uidb64: str) -> Any | None:
    """Decode user id URL-safe dan ambil user jika ada."""

    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        return User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return None


@require_POST
def sign_out(request: HttpRequest) -> HttpResponse:
    """Hapus sesi Django dan kembali ke landing page."""

    clear_pending_verification_user(request)
    logout(request)
    return redirect("home")


@guest_required
def forgot_password(request: HttpRequest) -> HttpResponse:
    """Kirim instruksi reset password tanpa bocorkan akun."""

    form = ForgotPasswordForm(data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        if not is_password_reset_rate_limited(request):
            users = User.objects.filter(email__iexact=form.cleaned_data["email"], is_active=True)
            for user in users:
                if can_send_password_reset_email(user):
                    send_password_reset_email(request, user)
        messages.success(request, "Jika email terdaftar, link reset password akan dikirim.")
        return redirect("signin")

    if request.method == "POST":
        messages.error(request, "Masukkan alamat email yang valid.")

    return render(request, "forgot_password.html", {"form": form, "hide_nav": True})


@guest_required
def password_reset_confirm(request: HttpRequest, uidb64: str, token: str) -> HttpResponse:
    """Validasi token reset dan izinkan pilih password baru."""

    user = get_user_from_uid(uidb64)
    token_valid = user and default_token_generator.check_token(user, token)
    if not token_valid:
        messages.error(request, "Link reset password tidak valid atau sudah kedaluwarsa.")
        return render(request, "auth/password_reset_invalid.html", {"hide_nav": True})

    form = PasswordResetConfirmForm(user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Password berhasil direset. Silakan login.")
        return redirect("signin")

    if request.method == "POST":
        for errors in form.errors.values():
            messages.error(request, errors[0])

    return render(request, "auth/password_reset_confirm.html", {"form": form, "hide_nav": True})
