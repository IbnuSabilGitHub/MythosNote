"""Embedding providers for source chunk vectorization (Backward compatibility layer).

All providers return vectors compatible with pgvector storage and similarity queries.
"""

from apps.sources.providers import (
    BaseEmbeddingProvider,
    OpenAIEmbeddingProvider,
    GeminiEmbeddingProvider,
    LocalEmbeddingProvider,
    _create_embedding_provider,
    _DefaultEmbeddingProvider,
    EmbeddingProvider,
)

__all__ = [
    "BaseEmbeddingProvider",
    "OpenAIEmbeddingProvider",
    "GeminiEmbeddingProvider",
    "LocalEmbeddingProvider",
    "_create_embedding_provider",
    "_DefaultEmbeddingProvider",
    "EmbeddingProvider",
]
