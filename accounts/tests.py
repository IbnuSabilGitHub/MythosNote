"""Tes integrasi untuk alur autentikasi."""

import re

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import UserUsage


@override_settings(
    ALLOWED_HOSTS=["testserver"],
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class AuthFlowTests(TestCase):
    """Cakup alur auth sesi tanpa fitur workspace."""

    def test_signup_requires_email_verification_before_full_access(self) -> None:
        response = self.client.post(
            reverse("signup"),
            {
                "username": "alice",
                "email": "alice@example.com",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
            },
        )

        self.assertRedirects(response, reverse("signin"))
        user = get_user_model().objects.get(username="alice")
        self.assertFalse(user.profile.email_verified)
        self.assertEqual(len(mail.outbox), 1)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

        verify_path = re.search(r"http://testserver(?P<path>/verify-email/\S+)", mail.outbox[0].body).group("path")
        verify_response = self.client.get(verify_path)

        self.assertRedirects(verify_response, reverse("signin"))
        user.refresh_from_db()
        self.assertTrue(user.profile.email_verified)
        self.assertFalse(verify_response.wsgi_request.user.is_authenticated)

    def test_verification_resend_is_rate_limited(self) -> None:
        user = get_user_model().objects.create_user(
            username="eve",
            email="eve@example.com",
            password="StrongPass123!",
        )
        self.client.login(username="eve", password="StrongPass123!")

        first = self.client.post(reverse("resend_verification"))
        second = self.client.post(reverse("resend_verification"))

        self.assertRedirects(first, reverse("email_unverified"))
        self.assertRedirects(second, reverse("email_unverified"))
        self.assertEqual(len(mail.outbox), 1)

    def test_verification_token_is_single_use(self) -> None:
        response = self.client.post(
            reverse("signup"),
            {
                "username": "carol",
                "email": "carol@example.com",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
            },
        )
        self.assertRedirects(response, reverse("signin"))
        verify_path = re.search(r"http://testserver(?P<path>/verify-email/\S+)", mail.outbox[0].body).group("path")

        self.assertRedirects(self.client.get(verify_path), reverse("signin"))
        replay = self.client.get(verify_path)

        self.assertEqual(replay.status_code, 200)
        self.assertTemplateUsed(replay, "auth/email_verification_invalid.html")

    def test_guest_only_routes_redirect_logged_in_users(self) -> None:
        user = get_user_model().objects.create_user(
            username="verified",
            email="verified@example.com",
            password="StrongPass123!",
        )
        user.profile.email_verified = True
        user.profile.save(update_fields=["email_verified"])

        self.client.login(username="verified", password="StrongPass123!")
        response = self.client.get(reverse("signin"))

        self.assertRedirects(response, reverse("home"))

    def test_failed_login_attempts_are_rate_limited(self) -> None:
        get_user_model().objects.create_user(
            username="bob",
            email="bob@example.com",
            password="StrongPass123!",
        )

        for _ in range(5):
            self.client.post(
                reverse("signin"),
                {"username": "bob", "password": "wrong-password"},
            )

        response = self.client.post(
            reverse("signin"),
            {"username": "bob", "password": "StrongPass123!"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        usage = UserUsage.objects.get(identifier="bob")
        self.assertEqual(usage.failed_login_count, 5)
