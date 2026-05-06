from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views.decorators.http import require_POST

from .decorators import guest_required
from .forms import ForgotPasswordForm, PasswordResetConfirmForm, SignInForm, SignUpForm
from .utils import (
    clear_failed_login_tracking,
    get_login_usage,
    is_email_verified,
    is_login_rate_limited,
    record_failed_login,
    send_password_reset_email,
    send_verification_email,
    verify_google_credential,
)


User = get_user_model()


@guest_required
def sign_in(request):
    """Handle session-based login with failed-attempt rate limiting."""

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
def sign_up(request):
    """Register a local account and send the first verification email."""

    form = SignUpForm(data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        send_verification_email(request, user)
        messages.success(request, "Akun berhasil dibuat. Silakan cek email untuk verifikasi.")
        return redirect("email_unverified")

    if request.method == "POST":
        for errors in form.errors.values():
            messages.error(request, errors[0])

    return render(request, "signup.html", {"form": form, "hide_nav": True})


@require_POST
@guest_required
def google_sign_in(request):
    """Create or login a user from a verified Google Identity Services credential."""

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


def get_or_create_google_user(payload):
    """Create a Django user from Google profile data without adding OAuth tables yet."""

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


def build_unique_username(email):
    """Generate a stable username seed from email and avoid collisions."""

    seed = email.split("@", 1)[0].replace(".", "_")[:140] or "user"
    username = seed
    suffix = 1
    while User.objects.filter(username__iexact=username).exists():
        suffix += 1
        username = f"{seed}_{suffix}"
    return username


@login_required
def email_unverified(request):
    """Show the verification gate for logged-in users with unverified email."""

    if is_email_verified(request.user):
        return redirect("home")
    return render(request, "auth/email_unverified.html")


@login_required
@require_POST
def resend_verification(request):
    """Resend verification email for the current logged-in account."""

    if is_email_verified(request.user):
        return redirect("home")
    send_verification_email(request, request.user)
    messages.success(request, "Link verifikasi baru sudah dikirim.")
    return redirect("email_unverified")


def verify_email(request, uidb64, token):
    """Verify a user's email from the signed token URL."""

    user = get_user_from_uid(uidb64)
    if user and default_token_generator.check_token(user, token):
        user.profile.email_verified = True
        user.profile.save(update_fields=["email_verified", "updated_at"])
        login(request, user)
        messages.success(request, "Email berhasil diverifikasi.")
        return redirect("home")

    messages.error(request, "Link verifikasi tidak valid atau sudah kedaluwarsa.")
    return render(request, "auth/email_verification_invalid.html")


def get_user_from_uid(uidb64):
    """Decode a URL-safe user id and return the matching user if it exists."""

    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        return User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return None


@require_POST
def sign_out(request):
    """Destroy the current Django session and return to the landing page."""

    logout(request)
    messages.success(request, "Anda sudah logout.")
    return redirect("home")


@guest_required
def forgot_password(request):
    """Send reset-password instructions while keeping account discovery private."""

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
def password_reset_confirm(request, uidb64, token):
    """Validate a reset token and allow the user to choose a new password."""

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
