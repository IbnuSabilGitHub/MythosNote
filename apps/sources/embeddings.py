"""Embedding providers for source chunk vectorization."""

from abc import ABC, abstractmethod

from django.conf import settings


class BaseEmbeddingProvider(ABC):
    """Abstract base for text embedding backends."""

    @abstractmethod
    def get_embedding(self, text: str) -> list[float]:
        """Return embedding vector for the given text."""


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """OpenAI text-embedding-3-small provider."""

    MODEL = "text-embedding-3-small"

    def __init__(self) -> None:
        from openai import OpenAI

        api_key = getattr(settings, "OPENAI_API_KEY", "") or ""
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not configured")
        self._client = OpenAI(api_key=api_key)

    def get_embedding(self, text: str) -> list[float]:
        response = self._client.embeddings.create(
            model=self.MODEL,
            input=text,
        )
        return list(response.data[0].embedding)


class GeminiEmbeddingProvider(BaseEmbeddingProvider):
    """Google Gemini embedding-001 provider."""

    MODEL = "models/embedding-001"

    def __init__(self) -> None:
        import google.generativeai as genai

        api_key = getattr(settings, "GEMINI_API_KEY", "") or ""
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not configured")
        genai.configure(api_key=api_key)
        self._client = genai

    def get_embedding(self, text: str) -> list[float]:
        result = self._client.embed_content(
            model=self.MODEL,
            content=text,
            task_type="retrieval_document",
        )
        return list(result["embedding"])


def _create_embedding_provider(name: str | None = None) -> BaseEmbeddingProvider:
    provider_name = (name or getattr(settings, "EMBEDDING_PROVIDER", "openai")).strip().lower()
    if provider_name == "openai":
        return OpenAIEmbeddingProvider()
    if provider_name == "gemini":
        return GeminiEmbeddingProvider()
    raise ValueError(
        f"Unsupported EMBEDDING_PROVIDER: {provider_name!r}. Use 'openai' or 'gemini'."
    )


class _DefaultEmbeddingProvider(BaseEmbeddingProvider):
    """Lazy default provider from EMBEDDING_PROVIDER setting."""

    _delegate: BaseEmbeddingProvider | None = None

    def get_embedding(self, text: str) -> list[float]:
        if self._delegate is None:
            self._delegate = _create_embedding_provider()
        return self._delegate.get_embedding(text)


EmbeddingProvider: BaseEmbeddingProvider = _DefaultEmbeddingProvider()
