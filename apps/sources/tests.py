"""Tests for AI providers selection and validation."""

from unittest.mock import patch

from django.test import TestCase, override_settings

from apps.sources.providers import (
    DeepSeekChatProvider,
    GeminiChatProvider,
    OpenAIChatProvider,
    _create_chat_provider,
    _create_embedding_provider,
    OpenAIEmbeddingProvider,
    GeminiEmbeddingProvider,
)


class AIProviderTests(TestCase):
    """Test suite for AI Provider selection, validation, and error fallback."""

    @override_settings(AI_PROVIDER="openai", OPENAI_API_KEY="test-key")
    @patch("openai.OpenAI")
    def test_provider_selection_openai(self, mock_openai) -> None:
        """Verify OpenAI chat provider is selected when AI_PROVIDER is openai."""
        provider = _create_chat_provider()
        self.assertIsInstance(provider, OpenAIChatProvider)

    @override_settings(AI_PROVIDER="gemini", GEMINI_API_KEY="test-key")
    @patch("google.generativeai.configure")
    def test_provider_selection_gemini(self, mock_configure) -> None:
        """Verify Gemini chat provider is selected when AI_PROVIDER is gemini."""
        provider = _create_chat_provider()
        self.assertIsInstance(provider, GeminiChatProvider)

    @override_settings(AI_PROVIDER="deepseek", DEEPSEEK_API_KEY="test-key")
    @patch("openai.OpenAI")
    def test_provider_selection_deepseek(self, mock_openai) -> None:
        """Verify DeepSeek chat provider is selected when AI_PROVIDER is deepseek."""
        provider = _create_chat_provider()
        self.assertIsInstance(provider, DeepSeekChatProvider)

    @override_settings(AI_PROVIDER="invalid")
    def test_provider_selection_invalid(self) -> None:
        """Verify ValueError is raised for invalid AI_PROVIDER settings."""
        with self.assertRaises(ValueError) as ctx:
            _create_chat_provider()
        self.assertIn("Unsupported AI_PROVIDER", str(ctx.exception))

    @override_settings(DEEPSEEK_API_KEY="")
    def test_deepseek_missing_api_key_raises_error(self) -> None:
        """Verify DeepSeekChatProvider raises ValueError if api key is missing."""
        with self.assertRaises(ValueError) as ctx:
            DeepSeekChatProvider()
        self.assertIn("DEEPSEEK_API_KEY is not configured", str(ctx.exception))

    @override_settings(OPENAI_API_KEY="")
    def test_openai_missing_api_key_raises_error(self) -> None:
        """Verify OpenAIChatProvider raises ValueError if api key is missing."""
        with self.assertRaises(ValueError) as ctx:
            OpenAIChatProvider()
        self.assertIn("OPENAI_API_KEY is not configured", str(ctx.exception))

    @override_settings(GEMINI_API_KEY="")
    def test_gemini_missing_api_key_raises_error(self) -> None:
        """Verify GeminiChatProvider raises ValueError if api key is missing."""
        with self.assertRaises(ValueError) as ctx:
            GeminiChatProvider()
        self.assertIn("GEMINI_API_KEY is not configured", str(ctx.exception))

    @override_settings(
        DEEPSEEK_API_KEY="test-deepseek-key",
        DEEPSEEK_BASE_URL="https://api.deepseek.com/v1",
    )
    @patch("openai.OpenAI")
    def test_deepseek_provider_uses_openai_sdk_with_correct_base_url(self, mock_openai_cls) -> None:
        """Verify DeepSeekChatProvider correctly forwards base_url to OpenAI SDK."""
        DeepSeekChatProvider()
        mock_openai_cls.assert_called_once_with(
            api_key="test-deepseek-key",
            base_url="https://api.deepseek.com/v1",
        )

    @override_settings(EMBEDDING_PROVIDER="openai", OPENAI_API_KEY="test-key")
    @patch("openai.OpenAI")
    def test_embedding_provider_selection_openai(self, mock_openai) -> None:
        """Verify OpenAI embedding provider is selected when EMBEDDING_PROVIDER is openai."""
        provider = _create_embedding_provider()
        self.assertIsInstance(provider, OpenAIEmbeddingProvider)

    @override_settings(EMBEDDING_PROVIDER="gemini", GEMINI_API_KEY="test-key")
    @patch("google.generativeai.configure")
    def test_embedding_provider_selection_gemini(self, mock_configure) -> None:
        """Verify Gemini embedding provider is selected when EMBEDDING_PROVIDER is gemini."""
        provider = _create_embedding_provider()
        self.assertIsInstance(provider, GeminiEmbeddingProvider)
