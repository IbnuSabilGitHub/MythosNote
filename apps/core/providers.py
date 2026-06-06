"""AI provider implementations for embeddings and chat/completions.

Shared providers used by apps.chat and apps.generate.
"""

import ipaddress as _ipaddress  # noqa: F401 — re-exported via providers shim
import time
from abc import ABC, abstractmethod
from typing import Any

import requests
from django.conf import settings


# ── Helpers ───────────────────────────────────────────────────────────────────

def _openrouter_headers(api_key: str) -> dict[str, str]:
    """Standard headers required by every OpenRouter API call."""
    return {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": getattr(settings, "FRONTEND_URL", "http://localhost:8000"),
        "X-Title": "MythosNote",
        "Content-Type": "application/json",
    }


# ── Embedding Providers ───────────────────────────────────────────────────────

class BaseEmbeddingProvider(ABC):
    """Abstract base for text embedding backends.

    All implementations must ensure that the output vector length matches
    the pgvector dimension configuration. Vector dimension consistency is
    critical for database storage and similarity queries.
    """

    @abstractmethod
    def get_embedding(self, text: str) -> list[float]:
        """Return embedding vector for the given text.

        Output vector length must match pgvector dimension.
        """

    def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Return list of embedding vectors for the given list of texts."""
        return [self.get_embedding(text) for text in texts]


class LocalEmbeddingProvider(BaseEmbeddingProvider):
    """Local/on-device embedding provider (placeholder).

    Reserved for future local embedding implementations.
    Useful for offline scenarios or when no API keys are available.
    """

    def __init__(self) -> None:
        raise NotImplementedError("LocalEmbeddingProvider is not yet implemented.")

    def get_embedding(self, text: str) -> list[float]:
        raise NotImplementedError("LocalEmbeddingProvider is not yet implemented.")


class OpenRouterEmbeddingProvider(BaseEmbeddingProvider):
    """OpenRouter embedding provider using REST API."""

    def __init__(self) -> None:
        self.api_key = getattr(settings, "OPENROUTER_API_KEY", "")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is not configured")
        self.model_name = getattr(settings, "EMBEDDING_MODEL", "openai/text-embedding-3-small")
        self.url = "https://openrouter.ai/api/v1/embeddings"

    def get_embedding(self, text: str) -> list[float]:
        return self.get_embeddings([text])[0]

    def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        payload = {"model": self.model_name, "input": texts}
        response = requests.post(self.url, headers=_openrouter_headers(self.api_key), json=payload, timeout=(5, 60))
        response.raise_for_status()
        return [item["embedding"] for item in response.json()["data"]]


def _create_embedding_provider(name: str | None = None) -> BaseEmbeddingProvider:
    """Instantiate embedding provider by name or EMBEDDING_PROVIDER setting."""
    provider_name = (name or getattr(settings, "EMBEDDING_PROVIDER", "openrouter")).strip().lower()
    if provider_name == "openrouter":
        return OpenRouterEmbeddingProvider()
    if provider_name == "local":
        return LocalEmbeddingProvider()
    raise ValueError(f"Unsupported EMBEDDING_PROVIDER: {provider_name!r}. Use 'openrouter' or 'local'.")


class _DefaultEmbeddingProvider(BaseEmbeddingProvider):
    """Lazy default provider from EMBEDDING_PROVIDER setting."""

    _delegate: BaseEmbeddingProvider | None = None

    def get_embedding(self, text: str) -> list[float]:
        if self._delegate is None:
            self._delegate = _create_embedding_provider()
        return self._delegate.get_embedding(text)

    def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        if self._delegate is None:
            self._delegate = _create_embedding_provider()
        return self._delegate.get_embeddings(texts)


EmbeddingProvider: BaseEmbeddingProvider = _DefaultEmbeddingProvider()


# ── Chat/Completion Providers ─────────────────────────────────────────────────

class BaseChatProvider(ABC):
    """Abstract base for chat/completion backends."""

    @abstractmethod
    def chat_complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """Generate chat completion response."""


class OpenRouterChatProvider(BaseChatProvider):
    """OpenRouter chat completion provider using REST API."""

    DEFAULT_MODEL = "deepseek/deepseek-chat"

    def __init__(self) -> None:
        self.api_key = getattr(settings, "OPENROUTER_API_KEY", "")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is not configured")
        self.url = "https://openrouter.ai/api/v1/chat/completions"

    def chat_complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        payload = {
            "model": kwargs.get("model", self.DEFAULT_MODEL),
            "messages": messages,
            "stream": False,
        }
        response = requests.post(self.url, headers=_openrouter_headers(self.api_key), json=payload, timeout=(5, 60))
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]


class GroqChatProvider(BaseChatProvider):
    """Groq chat completion provider using REST API."""

    DEFAULT_MODEL = "llama-3.3-70b-versatile"

    def __init__(self) -> None:
        self.api_key = getattr(settings, "GROQ_API_KEY", "")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is not configured")
        self.url = "https://api.groq.com/openai/v1/chat/completions"

    def chat_complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": kwargs.get("model", self.DEFAULT_MODEL),
            "messages": messages,
            "stream": False,
        }
        response = requests.post(self.url, headers=headers, json=payload, timeout=(5, 60))
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]


def _create_chat_provider(name: str | None = None) -> BaseChatProvider:
    """Instantiate chat provider by name or AI_PROVIDER setting."""
    provider_name = (name or getattr(settings, "AI_PROVIDER", "openrouter")).strip().lower()
    if provider_name == "openrouter":
        return OpenRouterChatProvider()
    if provider_name == "groq":
        return GroqChatProvider()
    raise ValueError(f"Unsupported AI_PROVIDER: {provider_name!r}. Use 'openrouter' or 'groq'.")


class _DefaultChatProvider(BaseChatProvider):
    """Lazy default chat provider from AI_PROVIDER setting."""

    _delegate: BaseChatProvider | None = None

    def chat_complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        if self._delegate is None:
            self._delegate = _create_chat_provider()
        return self._delegate.chat_complete(messages, **kwargs)


ChatProvider: BaseChatProvider = _DefaultChatProvider()
