"""Tests for generate API and processors."""

import json
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.generate.models import GenerateJob
from apps.generate.processors import ProcessOutputError, process_output
from apps.generate.services import GenerateContextError, get_generate_context
from apps.sources.models import Source, SourceChunk
from apps.workspaces.models import Workspace

User = get_user_model()


class ProcessOutputTests(TestCase):
    def test_quiz_valid_json(self):
        payload = {
            "questions": [
                {
                    "question": "Apa?",
                    "options": ["A. 1", "B. 2"],
                    "answer": "A",
                    "explanation": "karena",
                }
            ]
        }
        result = process_output("quiz", json.dumps(payload))
        self.assertEqual(json.loads(result)["questions"][0]["answer"], "A")

    def test_quiz_invalid_json(self):
        with self.assertRaises(ProcessOutputError):
            process_output("quiz", "not json")

    def test_mindmap_requires_prefix(self):
        out = process_output("mindmap", "mindmap\n  root((A))")
        self.assertTrue(out.startswith("mindmap"))

    def test_mindmap_invalid(self):
        with self.assertRaises(ProcessOutputError):
            process_output("mindmap", "graph TD\n  A-->B")


class GenerateAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="gen@test.com",
            email="gen@test.com",
            password="testpass123",
        )
        self.other = User.objects.create_user(
            username="other@test.com",
            email="other@test.com",
            password="testpass123",
        )
        self.workspace = Workspace.objects.create(user=self.user, name="WS")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_post_without_source_ids(self):
        url = reverse("workspace-generate", kwargs={"id": self.workspace.id})
        response = self.client.post(url, {"action": "summary"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_post_source_not_ready(self):
        source = Source.objects.create(
            user=self.user,
            workspace=self.workspace,
            original_filename="doc.txt",
            mime_type="text/plain",
            file_size=10,
            storage_path="x/doc.txt",
            status="processing",
        )
        url = reverse("workspace-generate", kwargs={"id": self.workspace.id})
        response = self.client.post(
            url,
            {"action": "summary", "source_ids": [str(source.id)]},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("konteks", response.json()["detail"].lower())

    @patch("apps.generate.views.check_and_increment_generate", return_value=True)
    @patch("apps.generate.views.django_rq.get_queue")
    def test_post_creates_job(self, mock_queue, _mock_quota):
        source = self._ready_source()
        mock_queue.return_value.enqueue.return_value = None

        url = reverse("workspace-generate", kwargs={"id": self.workspace.id})
        response = self.client.post(
            url,
            {"action": "summary", "source_ids": [str(source.id)]},
            format="json",
        )
        self.assertEqual(response.status_code, 202)
        job_id = response.json()["generate_job"]["id"]
        self.assertTrue(GenerateJob.objects.filter(id=job_id).exists())

    def test_get_job_other_user_404(self):
        job = GenerateJob.objects.create(
            user=self.other,
            workspace=Workspace.objects.create(user=self.other, name="Other"),
            action="summary",
            source_ids=[],
        )
        url = reverse("generate-job-detail", kwargs={"job_id": job.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    @patch("apps.generate.tasks.ChatProvider.chat_complete", return_value="not-json")
    def test_task_quiz_invalid_marks_failed(self, _mock_llm):
        source = self._ready_source()
        job = GenerateJob.objects.create(
            user=self.user,
            workspace=self.workspace,
            action="quiz",
            source_ids=[str(source.id)],
            options={"question_count": 5, "difficulty": "easy"},
            status="queued",
        )
        from apps.generate.tasks import process_generate_job

        process_generate_job(str(job.id))
        job.refresh_from_db()
        self.assertEqual(job.status, "failed")
        self.assertTrue(job.error_message)

    def _ready_source(self):
        source = Source.objects.create(
            user=self.user,
            workspace=self.workspace,
            original_filename="ready.txt",
            mime_type="text/plain",
            file_size=10,
            storage_path="x/ready.txt",
            status="ready",
        )
        SourceChunk.objects.create(
            source=source,
            chunk_index=0,
            text_content="Konteks uji coba generate.",
            token_count=5,
        )
        return source


class GenerateContextTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="ctx@test.com",
            email="ctx@test.com",
            password="testpass123",
        )
        self.workspace = Workspace.objects.create(user=self.user, name="CTX")

    def test_empty_source_ids_raises(self):
        with self.assertRaises(GenerateContextError):
            get_generate_context(
                user=self.user,
                workspace_id=self.workspace.id,
                source_ids=[],
            )
