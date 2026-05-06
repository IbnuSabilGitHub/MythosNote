from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect

from .utils import is_email_verified


def guest_required(view_func):
    """Redirect authenticated users away from auth-only pages."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("home")
        return view_func(request, *args, **kwargs)

    return wrapper


def verified_email_required(view_func):
    """Future-facing guard for workspace and core features."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not is_email_verified(request.user):
            messages.warning(request, "Verifikasi email diperlukan sebelum mengakses fitur ini.")
            return redirect("email_unverified")
        return view_func(request, *args, **kwargs)

    return wrapper
