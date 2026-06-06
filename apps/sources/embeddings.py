"""Embedding providers for source chunk vectorization (Backward compatibility layer).

All providers return vectors compatible with pgvector storage and similarity queries.
"""

from apps.core.providers import (
    BaseEmbeddingProvider,
    LocalEmbeddingProvider,
    _create_embedding_provider,
    _DefaultEmbeddingProvider,
    EmbeddingProvider,
)

__all__ = [
    "BaseEmbeddingProvider",
    "LocalEmbeddingProvider",
    "_create_embedding_provider",
    "_DefaultEmbeddingProvider",
    "EmbeddingProvider",
]
