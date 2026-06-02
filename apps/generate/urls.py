"""URLs for generate APIs."""

from django.urls import path

from apps.generate.views import GenerateJobDetailView, GenerateWorkspaceView

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
]
