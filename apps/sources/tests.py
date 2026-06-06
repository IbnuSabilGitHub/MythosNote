"""Tests for AI providers selection, validation, and security vulnerabilities."""

import os
from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.core.providers import (
    _create_chat_provider,
    _create_embedding_provider,
)
from apps.accounts.utils import get_client_ip
from apps.sources.tasks import extract_text_from_file


class AIProviderTests(TestCase):
    """Test suite for AI Provider selection, validation, and error fallback."""

    @override_settings(AI_PROVIDER="invalid")
    def test_provider_selection_invalid(self) -> None:
        """Verify ValueError is raised for invalid AI_PROVIDER settings."""
        with self.assertRaises(ValueError) as ctx:
            _create_chat_provider()
        self.assertIn("Unsupported AI_PROVIDER", str(ctx.exception))


class SecurityVulnerabilityTests(APITestCase):
    """Test suite targeting the fixed vulnerabilities."""

    def setUp(self):
        self.User = get_user_model()
        self.user = self.User.objects.create_user(username="testuser", email="test@mythosnote.local", password="password123")

    @override_settings(TRUSTED_PROXY_IPS=[])
    def test_xff_untrusted_by_default(self):
        """Verify X-Forwarded-For is ignored if TRUSTED_PROXY_IPS is empty."""
        request = MagicMock()
        request.META = {
            "REMOTE_ADDR": "127.0.0.1",
            "HTTP_X_FORWARDED_FOR": "203.0.113.195, 127.0.0.1"
        }
        ip = get_client_ip(request)
        self.assertEqual(ip, "127.0.0.1")

    @override_settings(TRUSTED_PROXY_IPS=["127.0.0.1"])
    def test_xff_trusted_when_configured(self):
        """Verify X-Forwarded-For is trusted only if REMOTE_ADDR is in TRUSTED_PROXY_IPS."""
        request = MagicMock()
        request.META = {
            "REMOTE_ADDR": "127.0.0.1",
            "HTTP_X_FORWARDED_FOR": "203.0.113.195, 127.0.0.1"
        }
        ip = get_client_ip(request)
        self.assertEqual(ip, "203.0.113.195")

    def test_parser_bomb_page_limit(self):
        """Verify extract_text_from_file raises ValueError if pages exceed MAX_EXTRACT_PAGES."""
        mock_doc = MagicMock()
        mock_doc.page_count = 1000  # Exceeds max 500 pages
        
        with patch("fitz.open", return_value=mock_doc):
            with self.assertRaises(ValueError) as ctx:
                extract_text_from_file("dummy.pdf", "application/pdf")
            self.assertIn("PDF terlalu banyak halaman", str(ctx.exception))

    def test_upload_file_with_too_long_filename(self):
        """Verify uploading file with name > 255 chars returns 400."""
        from apps.workspaces.models import Workspace
        workspace = Workspace.objects.create(user=self.user, name="Test WS")
        self.client.force_authenticate(user=self.user)

        long_filename = "a" * 160 + ".txt"
        file = SimpleUploadedFile(long_filename, b"content", content_type="text/plain")
        response = self.client.post(
            reverse("source-upload"),
            {"workspace_id": str(workspace.id), "file": file},
            format="multipart"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Nama file terlalu panjang", response.data["file"])
