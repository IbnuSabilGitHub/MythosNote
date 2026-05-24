"""Workspace quota helpers."""

from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import HttpRequest

from apps.accounts.utils import get_client_ip, increment_cache_counter
from apps.workspaces.models import Workspace

WORKSPACE_LIMIT = 10
WORKSPACE_MUTATION_RATE_LIMIT_ATTEMPTS = 60
WORKSPACE_MUTATION_RATE_LIMIT_WINDOW = 60


class WorkspaceQuotaExceeded(Exception):
    """Raised when a user has reached the workspace quota."""


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

    with transaction.atomic():
        locked_user = get_user_model().objects.select_for_update().get(pk=user.pk)
        if get_workspace_count(locked_user) >= WORKSPACE_LIMIT:
            raise WorkspaceQuotaExceeded
        return Workspace.objects.create(user=locked_user, name=name)


def is_workspace_mutation_rate_limited(request: HttpRequest, action: str) -> bool:
    identifier = request.user.pk if request.user.is_authenticated else get_client_ip(request) or "unknown"
    cache_key = f"workspace-mutation-rate:{action}:{identifier}"
    attempts = increment_cache_counter(cache_key, WORKSPACE_MUTATION_RATE_LIMIT_WINDOW)
    return attempts > WORKSPACE_MUTATION_RATE_LIMIT_ATTEMPTS
