"""Tes integrasi untuk alur autentikasi."""

import re

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from .views import get_or_create_google_user
from .models import UserUsage


@override_settings(
    ALLOWED_HOSTS=["testserver"],
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class AuthFlowTests(TestCase):
    """Cakup alur auth sesi tanpa fitur workspace."""

    def create_local_user(self, email: str, password: str, *, is_active: bool = True):
        user = get_user_model()(username=email, email=email, is_active=is_active)
        user.set_password(password)
        user.save()
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

        self.assertRedirects(response, reverse("signin"))
        user = get_user_model().objects.get(email="alice@gmail.com")
        self.assertFalse(user.is_active)
        self.assertFalse(user.profile.email_verified)
        self.assertEqual(len(mail.outbox), 1)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

        verify_path = re.search(r"http://testserver(?P<path>/verify-email/\S+)", mail.outbox[0].body).group("path")
        verify_response = self.client.get(verify_path)

        self.assertRedirects(verify_response, reverse("signin"))
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertTrue(user.profile.email_verified)
        self.assertFalse(verify_response.wsgi_request.user.is_authenticated)

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

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        self.assertEqual(len(mail.outbox), 0)
        self.assertContains(response, "pending@gmail.com", status_code=200)

    def test_verification_resend_is_rate_limited(self) -> None:
        self.create_local_user("eve@gmail.com", "StrongPass123!")
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
        self.assertRedirects(response, reverse("signin"))
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
        usage = UserUsage.objects.get(identifier="bob@gmail.com")
        self.assertEqual(usage.failed_login_count, 5)

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
