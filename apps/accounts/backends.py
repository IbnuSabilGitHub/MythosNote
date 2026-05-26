"""Custom authentication backends."""

from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.hashers import check_password, make_password


UserModel = get_user_model()
DUMMY_PASSWORD_HASH = make_password("mythosnote-dummy-password")


class EmailBackend(ModelBackend):
    """Authenticate using email/password only."""

    def authenticate(
        self,
        request: Any,
        username: str | None = None,
        password: str | None = None,
        **kwargs: Any,
    ) -> Any | None:
        email = (kwargs.get("email") or username or "").strip().lower()
        if not email or not password:
            return None

        user = UserModel.objects.filter(email__iexact=email, is_active=True).first()
        if user is None:
            check_password(password, DUMMY_PASSWORD_HASH)
            return None

        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
