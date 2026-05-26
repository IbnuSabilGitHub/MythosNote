"""URLs for source management APIs."""

from django.urls import path

from apps.sources.views import (
    ChatView,
    GenerateView,
    SourceDeleteView,
    SourceListView,
    SourceStatusView,
    SourceUploadView,
)


urlpatterns = [
    path("api/sources/", SourceListView.as_view(), name="source-list"),
    path("api/sources/upload/", SourceUploadView.as_view(), name="source-upload"),
    path("api/sources/<uuid:id>/", SourceDeleteView.as_view(), name="source-delete"),
    path("api/sources/<uuid:id>/status/", SourceStatusView.as_view(), name="source-status"),
    path("api/workspace/<uuid:id>/chat/", ChatView.as_view(), name="workspace-chat"),
    path("api/workspace/<uuid:id>/generate/", GenerateView.as_view(), name="workspace-generate"),
]
