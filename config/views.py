"""Tampilan level proyek untuk landing page publik dan halaman proyek."""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from accounts.decorators import verified_email_required


def home(request: HttpRequest) -> HttpResponse:
    """Render landing page publik dengan navigasi sadar auth."""

    return render(request, "home.html")


@verified_email_required
def project(request: HttpRequest) -> HttpResponse:
    """Render halaman proyek, hanya untuk user terverifikasi."""

    return render(request, "project.html")


@verified_email_required
def workspace(request: HttpRequest) -> HttpResponse:
    """Render halaman workspace."""

    return render(request, "workspace.html", {"show_navbar": False})
