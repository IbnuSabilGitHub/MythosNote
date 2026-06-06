"""URLs for generate APIs."""

from django.urls import path

from apps.generate.views import (
    GenerateJobDetailView,
    GenerateWorkspaceView,
    workspace_mindmap_view,
    workspace_quiz_view,
)

urlpatterns = [
    path(
        "api/workspace/<uuid:id>/generate/",
        GenerateWorkspaceView.as_view(),
        name="workspace-generate",
    ),
    path(
        "api/generate/<uuid:job_id>/",
        GenerateJobDetailView.as_view(),
        name="generate-job-detail",
    ),
    path(
        "workspace/quiz/<uuid:job_id>/",
        workspace_quiz_view,
        name="workspace_quiz",
    ),
    path(
        "workspace/mindmap/<uuid:job_id>/",
        workspace_mindmap_view,
        name="workspace_mindmap",
    ),
]
