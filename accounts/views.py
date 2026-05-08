"""Tampilan autentikasi untuk masuk, pendaftaran, dan verifikasi email."""

from typing import Any, Mapping

from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required
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
    clear_failed_login_tracking,
    email_verification_token_generator,
    get_verification_resend_wait_seconds,
    get_login_usage,
    is_google_oauth_rate_limited,
    is_email_verified,
    is_login_rate_limited,
    record_failed_login,
    send_password_reset_email,
    send_verification_email,
    verify_google_credential,
)


User = get_user_model()


@guest_required
def sign_in(request: HttpRequest) -> HttpResponse:
    """Tangani login sesi dengan pembatasan percobaan gagal."""

    form = SignInForm(request=request, data=request.POST or None)
    if request.method == "POST":
        usage = get_login_usage(request, request.POST.get("username", ""))
        if is_login_rate_limited(usage):
            messages.error(request, "Terlalu banyak percobaan login. Coba lagi beberapa menit lagi.")
        elif form.is_valid():
            login(request, form.user)
            clear_failed_login_tracking(usage)
            if not is_email_verified(form.user):
                return redirect("email_unverified")
            return redirect("home")
        else:
            record_failed_login(usage)
            messages.error(request, "Email/username atau password salah.")

    return render(request, "signin.html", {"form": form, "hide_nav": True})


@guest_required
def sign_up(request: HttpRequest) -> HttpResponse:
    """Daftarkan akun lokal dan kirim email verifikasi pertama."""


    form = SignUpForm(data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        send_verification_email(request, user)
        messages.success(request, "Akun berhasil dibuat. Cek email, lalu login setelah verifikasi.")
        return redirect("signin")

    if request.method == "POST" and not form.is_valid():
        # Extract backend validation errors and show as toast
        # Only email duplicates should be toast, others show in form
        email_errors = form.errors.get("email", [])
        if email_errors and "sudah terdaftar" in str(email_errors[0]).lower():
            messages.error(request, str(email_errors[0]))

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

    login(request, user)
    if not is_email_verified(user):
        return redirect("email_unverified")
    return redirect("home")


def get_or_create_google_user(payload: Mapping[str, Any]) -> Any:
    """Buat user Django dari data profil Google tanpa tabel OAuth."""

    with transaction.atomic():
        user = User.objects.select_for_update().filter(email__iexact=payload["email"]).first()
        if user is None:
            username = build_unique_username(payload["email"])
            user = User.objects.create_user(
                username=username,
                email=payload["email"],
                password=None,
            )
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


@login_required
def email_unverified(request: HttpRequest) -> HttpResponse:
    """Tampilkan gerbang verifikasi untuk user login yang belum verifikasi."""

    if is_email_verified(request.user):
        return redirect("home")
    return render(
        request,
        "auth/email_unverified.html",
        {"resend_wait_seconds": get_verification_resend_wait_seconds(request.user)},
    )


@login_required
@require_POST
def resend_verification(request: HttpRequest) -> HttpResponse:
    """Kirim ulang email verifikasi untuk akun login."""

    if is_email_verified(request.user):
        return redirect("home")
    if not can_send_verification_email(request.user):
        wait_seconds = get_verification_resend_wait_seconds(request.user)
        messages.warning(request, f"Tunggu {wait_seconds} detik sebelum kirim ulang.")
        return redirect("email_unverified")
    send_verification_email(request, request.user)
    messages.success(request, "Link verifikasi baru sudah dikirim.")
    return redirect("email_unverified")


def verify_email(request: HttpRequest, uidb64: str, token: str) -> HttpResponse:
    """Verifikasi email user dari URL token bertanda."""

    user = get_user_from_uid(uidb64)
    if user and email_verification_token_generator.check_token(user, token):
        user.profile.email_verified = True
        user.profile.save(update_fields=["email_verified", "updated_at"])
        if request.user.is_authenticated:
            logout(request)
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

    logout(request)
    return redirect("home")


@guest_required
def forgot_password(request: HttpRequest) -> HttpResponse:
    """Kirim instruksi reset password tanpa bocorkan akun."""

    form = ForgotPasswordForm(data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        users = User.objects.filter(email__iexact=form.cleaned_data["email"], is_active=True)
        for user in users:
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
