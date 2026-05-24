"""Workspace quota helpers."""

from apps.workspaces.models import Workspace

WORKSPACE_LIMIT = 10


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