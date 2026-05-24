"""Tampilan level proyek untuk landing page publik dan halaman proyek."""

from django.http import HttpRequest, HttpResponse
from django.contrib import messages
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.accounts.decorators import verified_email_required
from apps.workspaces.models import Workspace
from apps.workspaces.utils import WORKSPACE_LIMIT, get_workspace_quota


def home(request: HttpRequest) -> HttpResponse:
    """Render landing page publik dengan navigasi sadar auth."""

    return render(request, "home.html")


@verified_email_required
def project(request: HttpRequest) -> HttpResponse:
    """Render halaman proyek, hanya untuk user terverifikasi."""

    workspace_quota = get_workspace_quota(request.user)

    if request.method == "POST":
        if not workspace_quota["can_create"]:
            messages.warning(
                request,
                f"Batas workspace per user adalah {WORKSPACE_LIMIT}. Hapus workspace dulu untuk membuat yang baru.",
            )
            return redirect("project")

        workspace_name = (request.POST.get("name") or "").strip() or "Untitled Note"
        workspace = Workspace.objects.create(user=request.user, name=workspace_name)
        messages.success(request, f"Workspace '{workspace.name}' berhasil dibuat.")
        return redirect(f"{reverse('workspace')}?workspace_id={workspace.id}")

    workspaces = (
        Workspace.objects.filter(user=request.user)
        .annotate(source_count=Count("sources"))
        .order_by("-created_at")
    )

    return render(
        request,
        "project.html",
        {
            "workspaces": workspaces,
            "workspace_quota": workspace_quota,
        },
    )


@verified_email_required
def workspace(request: HttpRequest) -> HttpResponse:
    """Render halaman workspace."""

    workspace_id = request.GET.get("workspace_id")
    active_workspace = None

    if workspace_id:
        active_workspace = get_object_or_404(Workspace.objects.filter(user=request.user), id=workspace_id)

    return render(
        request,
        "workspace.html",
        {
            "show_navbar": False,
            "active_workspace": active_workspace,
        },
    )
