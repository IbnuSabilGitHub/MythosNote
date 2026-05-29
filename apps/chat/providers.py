"""Chat provider implementations for various AI backends."""

import os
from abc import ABC, abstractmethod
from functools import lru_cache

from django.conf import settings
import google.generativeai as genai
from openai import OpenAI


class BaseChatProvider(ABC):
    """Abstract base class for chat providers."""

    @abstractmethod
    def generate(self, prompt: str, context: str = "") -> str:
        """Generate a response from the chat provider."""
        pass


class GeminiChatProvider(BaseChatProvider):
    """Gemini chat provider implementation."""

    def __init__(self):
        api_key = getattr(settings, "GEMINI_API_KEY", "")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not configured in settings.")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def generate(self, prompt: str, context: str = "") -> str:
        full_prompt = f"{context}\n\n{prompt}".strip()
        response = self.model.generate_content(full_prompt)
        return response.text


class DeepSeekChatProvider(BaseChatProvider):
    """DeepSeek chat provider implementation using the OpenAI SDK."""

    def __init__(self):
        api_key = getattr(settings, "DEEPSEEK_API_KEY", "")
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY is not configured in settings.")
        base_url = getattr(settings, "DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = 'deepseek-chat'

    def generate(self, prompt: str, context: str = "") -> str:
        messages = []
        if context:
            messages.append({"role": "system", "content": context})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
        )
        return response.choices[0].message.content or ""


class ChatProviderFactory:
    """Factory for creating chat providers."""

    @staticmethod
    @lru_cache(maxsize=None)
    def get_provider(provider_name: str | None = None) -> BaseChatProvider:
        """Get a chat provider instance based on the provider name."""
        if provider_name is None:
            provider_name = getattr(settings, "AI_PROVIDER", "gemini").lower()

        if provider_name == 'gemini':
            return GeminiChatProvider()
        elif provider_name == 'deepseek':
            return DeepSeekChatProvider()
        else:
            raise ValueError(f"Unsupported AI_PROVIDER: {provider_name}")

# Default provider instance
ChatProvider = ChatProviderFactory.get_provider()
