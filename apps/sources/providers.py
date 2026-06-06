"""Backward-compatibility shim for apps.sources.providers.

ChatProvider dan EmbeddingProvider dipindah ke apps.core.providers (refactor 2026-06-06).
Import dari apps.core.providers untuk kode baru.
"""

# Re-export agar kode lama yang masih import dari sini tidak langsung patah.
from apps.core.providers import (  # noqa: F401
    BaseEmbeddingProvider,
    LocalEmbeddingProvider,
    OpenRouterEmbeddingProvider,
    BaseChatProvider,
    OpenRouterChatProvider,
    GroqChatProvider,
    EmbeddingProvider,
    ChatProvider,
)
