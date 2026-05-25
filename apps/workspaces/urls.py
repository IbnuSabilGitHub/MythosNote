from django.urls import path
from .views import WorkspaceDeleteView, WorkspaceRenameView

urlpatterns = [
    path("api/workspaces/<uuid:id>/rename/", WorkspaceRenameView.as_view(), name="workspace-rename"),
    path("api/workspaces/<uuid:id>/", WorkspaceDeleteView.as_view(), name="workspace-delete"),
]
