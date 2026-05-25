"""Tests untuk validasi workspace."""

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.workspaces.models import Workspace


@override_settings(ALLOWED_HOSTS=["testserver"])
class WorkspaceNameValidationTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(
            username="tester@example.com",
            email="tester@example.com",
            password="StrongPass123!",
        )
        self.user.profile.email_verified = True
        self.user.profile.save(update_fields=["email_verified"])
        self.client.login(username="tester@example.com", password="StrongPass123!")

    def test_project_create_rejects_overlong_workspace_name(self) -> None:
        response = self.client.post(
            reverse("project"),
            {"name": "a" * 81},
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Nama workspace maksimal 80 karakter.", status_code=400)
        self.assertEqual(Workspace.objects.count(), 0)

    def test_project_create_renders_name_limit(self) -> None:
        response = self.client.get(reverse("project"))

        self.assertContains(response, 'maxlength="80"')
        self.assertContains(response, "data-workspace-name-counter")

    def test_workspace_rename_rejects_overlong_workspace_name(self) -> None:
        workspace = Workspace.objects.create(user=self.user, name="Existing Workspace")

        response = self.client.post(
            reverse("workspace-rename", args=[workspace.id]),
            {"name": "b" * 81},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["name"], "Nama workspace maksimal 80 karakter.")
        workspace.refresh_from_db()
        self.assertEqual(workspace.name, "Existing Workspace")