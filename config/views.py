"""Tampilan level proyek untuk landing page publik dan halaman proyek."""

from django.http import HttpRequest, HttpResponse
from django.contrib import messages
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.accounts.decorators import verified_email_required
from apps.workspaces.models import Workspace
from apps.workspaces.utils import (
    WORKSPACE_LIMIT,
    WorkspaceQuotaExceeded,
    WorkspaceNameValidationError,
    clean_workspace_name,
    create_workspace_for_user,
    get_workspace_quota,
    is_workspace_mutation_rate_limited,
    WORKSPACE_NAME_MAX_LENGTH,
)


def home(request: HttpRequest) -> HttpResponse:
    """Render landing page publik dengan navigasi sadar auth."""

    return render(request, "home.html")


@verified_email_required
def project(request: HttpRequest) -> HttpResponse:
    """Render halaman proyek, hanya untuk user terverifikasi."""

    if request.method == "POST":
        if is_workspace_mutation_rate_limited(request, "create"):
            messages.warning(request, "Terlalu banyak request. Coba lagi sebentar.")
            return _render_project(request, status_code=429)

        try:
            workspace_name = clean_workspace_name(request.POST.get("name"), default_if_blank="Untitled Note")
        except WorkspaceNameValidationError as exc:
            messages.error(request, exc.messages[0])
            return _render_project(request, status_code=400)

        try:
            workspace = create_workspace_for_user(request.user, workspace_name)
        except WorkspaceQuotaExceeded:
            messages.warning(
                request,
                f"Batas workspace per user adalah {WORKSPACE_LIMIT}. Hapus workspace dulu untuk membuat yang baru.",
            )
            return _render_project(request, status_code=409)

        messages.success(request, f"Workspace '{workspace.name}' berhasil dibuat.")
        return redirect(f"{reverse('workspace')}?workspace_id={workspace.id}")

    return _render_project(request)


def _render_project(request: HttpRequest, *, status_code: int = 200) -> HttpResponse:
    workspace_quota = get_workspace_quota(request.user)

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
            "workspace_name_max_length": WORKSPACE_NAME_MAX_LENGTH,
        },
        status=status_code,
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
