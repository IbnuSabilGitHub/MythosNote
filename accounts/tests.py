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
    """Cover the session auth flow without touching future workspace features."""

    def test_signup_requires_email_verification_before_full_access(self):
        response = self.client.post(
            reverse("signup"),
            {
                "username": "alice",
                "email": "alice@example.com",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
            },
        )

        self.assertRedirects(response, reverse("email_unverified"))
        user = get_user_model().objects.get(username="alice")
        self.assertFalse(user.profile.email_verified)
        self.assertEqual(len(mail.outbox), 1)

        verify_path = re.search(r"http://testserver(?P<path>/verify-email/\S+)", mail.outbox[0].body).group("path")
        verify_response = self.client.get(verify_path)

        self.assertRedirects(verify_response, reverse("home"))
        user.refresh_from_db()
        self.assertTrue(user.profile.email_verified)

    def test_guest_only_routes_redirect_logged_in_users(self):
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

    def test_failed_login_attempts_are_rate_limited(self):
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
