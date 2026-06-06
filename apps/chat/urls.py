"""URL routes untuk chat API.

URL endpoints tidak diubah agar frontend aman.
Dipindah dari apps.sources.urls selama refactor (2026-06-06).
"""

from django.urls import path

from apps.chat.views import (
    ChatView,
    ChatSessionListView,
    ChatMessageListView,
    ChatMessageDeleteView,
)

urlpatterns = [
    path("api/workspace/<uuid:id>/chat/", ChatView.as_view(), name="workspace-chat"),
    path("api/workspace/<uuid:id>/chat/sessions/", ChatSessionListView.as_view(), name="workspace-chat-sessions"),
    path("api/chat/session/<uuid:session_id>/messages/", ChatMessageListView.as_view(), name="chat-session-messages"),
    path("api/workspace/<uuid:id>/chat/messages/", ChatMessageDeleteView.as_view(), name="workspace-chat-messages-delete"),
]
