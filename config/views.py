"""Tampilan level proyek untuk landing page publik dan halaman proyek."""

from django.http import HttpRequest, HttpResponse
from django.contrib import messages
from django.db.models import Count
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.accounts.decorators import verified_email_required
from apps.workspaces.models import Workspace


def home(request: HttpRequest) -> HttpResponse:
    """Render landing page publik dengan navigasi sadar auth."""

    return render(request, "home.html")


@verified_email_required
def project(request: HttpRequest) -> HttpResponse:
    """Render halaman proyek, hanya untuk user terverifikasi."""

    if request.method == "POST":
        workspace_name = (request.POST.get("name") or "").strip() or "Untitled Note"
        workspace = Workspace.objects.create(user=request.user, name=workspace_name)
        messages.success(request, f"Workspace '{workspace.name}' berhasil dibuat.")
        return redirect(f"{reverse('workspace')}?workspace_id={workspace.id}")

    workspaces = (
        Workspace.objects.filter(user=request.user)
        .annotate(source_count=Count("sources"))
        .order_by("-created_at")
    )

    return render(request, "project.html", {"workspaces": workspaces})


@verified_email_required
def workspace(request: HttpRequest) -> HttpResponse:
    """Render halaman workspace."""

    return render(request, "workspace.html", {"show_navbar": False})
