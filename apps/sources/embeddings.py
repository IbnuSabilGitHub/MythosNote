"""Embedding providers for source chunk vectorization (Backward compatibility layer)."""

from apps.sources.providers import (
    BaseEmbeddingProvider,
    OpenAIEmbeddingProvider,
    GeminiEmbeddingProvider,
    _create_embedding_provider,
    _DefaultEmbeddingProvider,
    EmbeddingProvider,
)

__all__ = [
    "BaseEmbeddingProvider",
    "OpenAIEmbeddingProvider",
    "GeminiEmbeddingProvider",
    "_create_embedding_provider",
    "_DefaultEmbeddingProvider",
    "EmbeddingProvider",
]
