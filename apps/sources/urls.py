"""URLs for source management APIs."""

from django.urls import path

from apps.sources.views import (
    ChatView,
    SourceDeleteView,
    SourceListView,
    SourceStatusView,
    SourceUploadView,
    SourceDownloadView,
    ChatSessionListView,
    ChatMessageListView,
    ChatMessageDeleteView,
)


urlpatterns = [
    path("api/sources/", SourceListView.as_view(), name="source-list"),
    path("api/sources/upload/", SourceUploadView.as_view(), name="source-upload"),
    path("api/sources/<uuid:id>/", SourceDeleteView.as_view(), name="source-delete"),
    path("api/sources/<uuid:id>/download/", SourceDownloadView.as_view(), name="source-download"),
    path("api/sources/<uuid:id>/status/", SourceStatusView.as_view(), name="source-status"),
    path("api/workspace/<uuid:id>/chat/", ChatView.as_view(), name="workspace-chat"),
    path("api/workspace/<uuid:id>/chat/sessions/", ChatSessionListView.as_view(), name="workspace-chat-sessions"),
    path("api/chat/session/<uuid:session_id>/messages/", ChatMessageListView.as_view(), name="chat-session-messages"),
    path("api/workspace/<uuid:id>/chat/messages/", ChatMessageDeleteView.as_view(), name="workspace-chat-messages-delete"),
]
