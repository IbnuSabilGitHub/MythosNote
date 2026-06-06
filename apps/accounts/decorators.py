"""Decorator untuk menjaga view auth-only dan verifikasi."""

from typing import Any, Callable
from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect

from .utils import is_email_verified


def guest_required(view_func: Callable[..., HttpResponse]) -> Callable[..., HttpResponse]:
    """Arahkan user login menjauh dari halaman auth-only."""

    @wraps(view_func)
    def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if request.user.is_authenticated:
            return redirect("home")
        return view_func(request, *args, **kwargs)

    return wrapper


def verified_email_required(view_func: Callable[..., HttpResponse]) -> Callable[..., HttpResponse]:
    """Guard untuk fitur workspace dan inti."""

    @wraps(view_func)
    def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not is_email_verified(request.user):
            messages.warning(request, "Verifikasi email diperlukan sebelum mengakses fitur ini.")
            return redirect("email_unverified")
        if not request.user.first_name:
            return redirect("onboarding")
        return view_func(request, *args, **kwargs)

    return wrapper
