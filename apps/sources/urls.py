"""URLs for source management APIs.

Chat URLs dipindah ke apps.chat.urls (refactor 2026-06-06).
"""

from django.urls import path

from apps.sources.views import (
    SourceDeleteView,
    SourceListView,
    SourceStatusView,
    SourceUploadView,
    SourceDownloadView,
)


urlpatterns = [
    path("api/sources/", SourceListView.as_view(), name="source-list"),
    path("api/sources/upload/", SourceUploadView.as_view(), name="source-upload"),
    path("api/sources/<uuid:id>/", SourceDeleteView.as_view(), name="source-delete"),
    path("api/sources/<uuid:id>/download/", SourceDownloadView.as_view(), name="source-download"),
    path("api/sources/<uuid:id>/status/", SourceStatusView.as_view(), name="source-status"),
]
