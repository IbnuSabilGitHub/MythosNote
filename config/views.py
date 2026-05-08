"""Project-level page views for the public landing page and workspace page."""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from accounts.decorators import verified_email_required


def home(request: HttpRequest) -> HttpResponse:
    """Render the public landing page with auth-aware navigation."""

    return render(request, "home.html")


@verified_email_required
def project(request: HttpRequest) -> HttpResponse:
    """Render the project page, accessible only for verified users."""

    return render(request, "project.html", {"hide_nav": True})
