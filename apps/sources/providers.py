"""AI provider implementations for embeddings and chat/completions."""

from abc import ABC, abstractmethod
from typing import Any

from django.conf import settings


# Embedding Providers
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


# ==============================================================================
# Chat/Completion Providers
# ==============================================================================

class BaseChatProvider(ABC):
    """Abstract base for chat/completion backends."""

    @abstractmethod
    def chat_complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """Generate chat completion response."""


class OpenAIChatProvider(BaseChatProvider):
    """OpenAI chat completion provider."""

    MODEL = "gpt-4o"

    def __init__(self) -> None:
        from openai import OpenAI

        api_key = getattr(settings, "OPENAI_API_KEY", "") or ""
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not configured")
        self._client = OpenAI(api_key=api_key)

    def chat_complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        model_name = kwargs.get("model", self.MODEL)
        api_kwargs = {k: v for k, v in kwargs.items() if k != "model"}
        response = self._client.chat.completions.create(
            model=model_name,
            messages=messages,  # type: ignore
            **api_kwargs,
        )
        return response.choices[0].message.content or ""


class GeminiChatProvider(BaseChatProvider):
    """Google Gemini chat completion provider."""

    MODEL = "gemini-2.0-flash"

    def __init__(self) -> None:
        import google.generativeai as genai

        api_key = getattr(settings, "GEMINI_API_KEY", "") or ""
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not configured")
        genai.configure(api_key=api_key)
        self._client = genai

    def chat_complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        gemini_messages = []
        system_instruction = None
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                system_instruction = content
            else:
                gemini_role = "user" if role == "user" else "model"
                gemini_messages.append({"role": gemini_role, "parts": [content]})

        model_name = kwargs.get("model", self.MODEL)
        model = self._client.GenerativeModel(
            model_name=model_name,
            system_instruction=system_instruction,
        )
        response = model.generate_content(gemini_messages)
        return response.text


class DeepSeekChatProvider(BaseChatProvider):
    """DeepSeek chat completion provider using OpenAI SDK."""

    MODEL = "deepseek-chat"

    def __init__(self) -> None:
        from openai import OpenAI

        api_key = getattr(settings, "DEEPSEEK_API_KEY", "") or ""
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY is not configured")
        base_url = getattr(settings, "DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1") or "https://api.deepseek.com/v1"
        self._client = OpenAI(api_key=api_key, base_url=base_url)

    def chat_complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        model_name = kwargs.get("model", self.MODEL)
        api_kwargs = {k: v for k, v in kwargs.items() if k != "model"}
        response = self._client.chat.completions.create(
            model=model_name,
            messages=messages,  # type: ignore
            **api_kwargs,
        )
        return response.choices[0].message.content or ""


def _create_chat_provider(name: str | None = None) -> BaseChatProvider:
    provider_name = (name or getattr(settings, "AI_PROVIDER", "gemini")).strip().lower()
    if provider_name == "openai":
        return OpenAIChatProvider()
    if provider_name == "gemini":
        return GeminiChatProvider()
    if provider_name == "deepseek":
        return DeepSeekChatProvider()
    raise ValueError(
        f"Unsupported AI_PROVIDER: {provider_name!r}. Use 'gemini', 'openai', or 'deepseek'."
    )


class _DefaultChatProvider(BaseChatProvider):
    """Lazy default chat provider from AI_PROVIDER setting."""

    _delegate: BaseChatProvider | None = None

    def chat_complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        if self._delegate is None:
            self._delegate = _create_chat_provider()
        return self._delegate.chat_complete(messages, **kwargs)


ChatProvider: BaseChatProvider = _DefaultChatProvider()
