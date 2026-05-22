"""URLs for source management APIs."""

from django.urls import path

from apps.sources.views import (
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
]
