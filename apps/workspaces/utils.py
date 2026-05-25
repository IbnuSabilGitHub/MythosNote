"""Workspace quota helpers."""

from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import HttpRequest

from apps.accounts.utils import get_client_ip, increment_cache_counter
from apps.workspaces.models import Workspace

WORKSPACE_LIMIT = 10
WORKSPACE_NAME_MAX_LENGTH = 40
WORKSPACE_MUTATION_RATE_LIMIT_ATTEMPTS = 60
WORKSPACE_MUTATION_RATE_LIMIT_WINDOW = 60


class WorkspaceQuotaExceeded(Exception):
    """Raised when a user has reached the workspace quota."""


class WorkspaceNameValidationError(ValidationError):
    """Raised when a workspace name fails application-level validation."""


def clean_workspace_name(name: str | None, *, default_if_blank: str | None = None) -> str:
    cleaned_name = (name or "").strip()

    if not cleaned_name:
        if default_if_blank is not None:
            return default_if_blank
        raise WorkspaceNameValidationError("Nama workspace wajib diisi.")

    if len(cleaned_name) > WORKSPACE_NAME_MAX_LENGTH:
        raise WorkspaceNameValidationError(
            f"Nama workspace maksimal {WORKSPACE_NAME_MAX_LENGTH} karakter."
        )

    return cleaned_name


def get_workspace_count(user):
    return Workspace.objects.filter(user=user).count()


def get_workspace_quota(user):
    workspace_count = get_workspace_count(user)
    return {
        "count": workspace_count,
        "limit": WORKSPACE_LIMIT,
        "remaining": max(WORKSPACE_LIMIT - workspace_count, 0),
        "can_create": workspace_count < WORKSPACE_LIMIT,
    }


def create_workspace_for_user(user, name: str) -> Workspace:
    """Create a workspace after locking the owning user row."""

    cleaned_name = clean_workspace_name(name, default_if_blank="Untitled Note")

    with transaction.atomic():
        locked_user = get_user_model().objects.select_for_update().get(pk=user.pk)
        if get_workspace_count(locked_user) >= WORKSPACE_LIMIT:
            raise WorkspaceQuotaExceeded
        return Workspace.objects.create(user=locked_user, name=cleaned_name)


def is_workspace_mutation_rate_limited(request: HttpRequest, action: str) -> bool:
    identifier = request.user.pk if request.user.is_authenticated else get_client_ip(request) or "unknown"
    cache_key = f"workspace-mutation-rate:{action}:{identifier}"
    attempts = increment_cache_counter(cache_key, WORKSPACE_MUTATION_RATE_LIMIT_WINDOW)
    return attempts > WORKSPACE_MUTATION_RATE_LIMIT_ATTEMPTS
