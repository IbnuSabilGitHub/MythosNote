"""Tes integrasi untuk alur autentikasi."""

import re
from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .views import get_or_create_google_user
from .models import UserUsage


@override_settings(
    ALLOWED_HOSTS=["testserver"],
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    SECURE_SSL_REDIRECT=False,
    SESSION_COOKIE_SECURE=False,
    CSRF_COOKIE_SECURE=False,
)
class AuthFlowTests(TestCase):
    """Cakup alur auth sesi tanpa fitur workspace."""

    def create_local_user(self, email: str, password: str, *, is_active: bool = True):
        user = get_user_model()(username=email, email=email, is_active=is_active)
        user.set_password(password)
        user.save()
        return user

    def create_stale_unverified_user(self, email: str, *, days_old: int = 2):
        user = self.create_local_user(email, "StrongPass123!", is_active=False)
        user.date_joined = timezone.now() - timedelta(days=days_old)
        user.save(update_fields=["date_joined"])
        user.profile.email_verified = False
        user.profile.save(update_fields=["email_verified"])
        return user

    def test_signup_requires_email_verification_before_full_access(self) -> None:
        response = self.client.post(
            reverse("signup"),
            {
                "email": "alice@gmail.com",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
            },
        )

        self.assertRedirects(response, reverse("email_unverified"))
        user = get_user_model().objects.get(email="alice@gmail.com")
        self.assertFalse(user.is_active)
        self.assertFalse(user.profile.email_verified)
        self.assertEqual(len(mail.outbox), 1)
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        self.assertEqual(self.client.session.get("pending_verification_user_id"), user.pk)

        verify_path = re.search(r"http://testserver(?P<path>/verify-email/\S+)", mail.outbox[0].body).group("path")
        verify_response = self.client.get(verify_path)

        self.assertRedirects(verify_response, reverse("signin"))
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertTrue(user.profile.email_verified)
        self.assertFalse(verify_response.wsgi_request.user.is_authenticated)
        self.assertNotIn("pending_verification_user_id", self.client.session)

    def test_inactive_user_cannot_login_before_verification(self) -> None:
        self.client.post(
            reverse("signup"),
            {
                "email": "pending@gmail.com",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
            },
        )

        mail.outbox.clear()
        response = self.client.post(
            reverse("signin"),
            {
                "email": "pending@gmail.com",
                "password": "StrongPass123!",
            },
        )

        self.assertRedirects(response, reverse("email_unverified"))
        follow_response = self.client.get(reverse("email_unverified"))
        self.assertFalse(follow_response.wsgi_request.user.is_authenticated)
        self.assertEqual(len(mail.outbox), 0)
        self.assertContains(follow_response, "Email belum terverifikasi", status_code=200)

    def test_verification_resend_is_rate_limited(self) -> None:
        user = self.create_local_user("eve@gmail.com", "StrongPass123!")
        user.profile.email_verified = False
        user.profile.save(update_fields=["email_verified"])
        self.client.login(username="eve@gmail.com", password="StrongPass123!")

        first = self.client.post(reverse("resend_verification"))
        second = self.client.post(reverse("resend_verification"))

        self.assertRedirects(first, reverse("email_unverified"))
        self.assertRedirects(second, reverse("email_unverified"))
        self.assertEqual(len(mail.outbox), 1)

    def test_verification_token_is_single_use(self) -> None:
        response = self.client.post(
            reverse("signup"),
            {
                "email": "carol@gmail.com",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
            },
        )
        self.assertRedirects(response, reverse("email_unverified"))
        verify_path = re.search(r"http://testserver(?P<path>/verify-email/\S+)", mail.outbox[0].body).group("path")

        self.assertRedirects(self.client.get(verify_path), reverse("signin"))
        replay = self.client.get(verify_path)

        self.assertEqual(replay.status_code, 200)
        self.assertTemplateUsed(replay, "auth/email_verification_invalid.html")

    def test_guest_only_routes_redirect_logged_in_users(self) -> None:
        user = self.create_local_user("verified@gmail.com", "StrongPass123!")
        user.profile.email_verified = True
        user.profile.save(update_fields=["email_verified"])

        self.client.login(username="verified@gmail.com", password="StrongPass123!")
        response = self.client.get(reverse("signin"))

        self.assertRedirects(response, reverse("home"))

    def test_failed_login_attempts_are_rate_limited(self) -> None:
        self.create_local_user("bob@gmail.com", "StrongPass123!")

        for _ in range(5):
            self.client.post(
                reverse("signin"),
                {"email": "bob@gmail.com", "password": "wrong-password"},
            )

        response = self.client.post(
            reverse("signin"),
            {"email": "bob@gmail.com", "password": "StrongPass123!"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        usage = UserUsage.objects.get(identifier__startswith="bob@gmail.com|")
        self.assertEqual(usage.failed_login_count, 5)

    def test_signup_existing_email_uses_generic_confirmation(self) -> None:
        self.create_local_user("known@gmail.com", "StrongPass123!")

        response = self.client.post(
            reverse("signup"),
            {
                "email": "known@gmail.com",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
            },
        )

        self.assertRedirects(response, reverse("email_unverified"))
        follow_response = self.client.get(reverse("email_unverified"))
        self.assertContains(follow_response, "Jika email dapat digunakan", status_code=200)
        self.assertNotContains(follow_response, 'id="resend-verification-button"')
        self.assertEqual(len(mail.outbox), 0)

    def test_email_unverified_rejects_arbitrary_email_lookup(self) -> None:
        self.create_local_user("target@gmail.com", "StrongPass123!", is_active=False)

        response = self.client.get(reverse("email_unverified"), {"email": "target@gmail.com"})

        self.assertRedirects(response, reverse("signin"))

    def test_resend_verification_requires_bound_session_or_authenticated_user(self) -> None:
        self.create_local_user("target@gmail.com", "StrongPass123!", is_active=False)

        response = self.client.post(
            reverse("resend_verification"),
            {"email": "target@gmail.com"},
        )

        self.assertRedirects(response, reverse("signin"))
        self.assertEqual(len(mail.outbox), 0)

    def test_inactive_login_does_not_auto_resend_verification_email(self) -> None:
        self.client.post(
            reverse("signup"),
            {
                "email": "quiet@gmail.com",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
            },
        )

        mail.outbox.clear()
        response = self.client.post(
            reverse("signin"),
            {
                "email": "quiet@gmail.com",
                "password": "StrongPass123!",
            },
        )

        self.assertRedirects(response, reverse("email_unverified"))
        self.assertEqual(len(mail.outbox), 0)

    def test_forgot_password_is_throttled_without_leaking_account_status(self) -> None:
        self.create_local_user("reset@gmail.com", "StrongPass123!")

        first = self.client.post(
            reverse("forgot_password"),
            {"email": "reset@gmail.com"},
        )
        second = self.client.post(
            reverse("forgot_password"),
            {"email": "reset@gmail.com"},
        )

        self.assertRedirects(first, reverse("signin"))
        self.assertRedirects(second, reverse("signin"))
        self.assertEqual(len(mail.outbox), 1)

    def test_google_user_creation_sets_username(self) -> None:
        user = get_or_create_google_user(
            {
                "email": "google.user@gmail.com",
                "email_verified": True,
            }
        )

        self.assertIsNone(user.username)
        self.assertEqual(user.email, "google.user@gmail.com")
        self.assertTrue(user.profile.email_verified)

    def test_cleanup_unverified_users_dry_run_keeps_data(self) -> None:
        stale_user = self.create_stale_unverified_user("stale@gmail.com")
        output = StringIO()

        call_command(
            "cleanup_unverified_users",
            "--dry-run",
            "--days=1",
            stdout=output,
        )

        stale_user.refresh_from_db()
        self.assertIn("stale@gmail.com", output.getvalue())
        self.assertTrue(get_user_model().objects.filter(pk=stale_user.pk).exists())

    def test_cleanup_unverified_users_deletes_only_matching_users(self) -> None:
        stale_user = self.create_stale_unverified_user("delete-me@gmail.com")
        keep_verified = self.create_local_user("keep-verified@gmail.com", "StrongPass123!", is_active=False)
        keep_verified.date_joined = timezone.now() - timedelta(days=3)
        keep_verified.save(update_fields=["date_joined"])
        keep_verified.profile.email_verified = True
        keep_verified.profile.save(update_fields=["email_verified"])

        keep_active = self.create_local_user("keep-active@gmail.com", "StrongPass123!", is_active=True)
        keep_active.date_joined = timezone.now() - timedelta(days=3)
        keep_active.save(update_fields=["date_joined"])

        output = StringIO()
        with patch("builtins.input", return_value="yes"):
            call_command(
                "cleanup_unverified_users",
                "--days=1",
                "--batch-size=1",
                stdout=output,
            )

        self.assertFalse(get_user_model().objects.filter(pk=stale_user.pk).exists())
        self.assertTrue(get_user_model().objects.filter(pk=keep_verified.pk).exists())
        self.assertTrue(get_user_model().objects.filter(pk=keep_active.pk).exists())
        self.assertIn("delete-me@gmail.com", output.getvalue())
