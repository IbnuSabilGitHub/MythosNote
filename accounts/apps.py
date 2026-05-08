"""App configuration for the accounts app."""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Register account models and signal hooks for authentication state."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"

    def ready(self) -> None:
        """Load signal handlers once Django's app registry is ready."""

        import accounts.signals  # noqa: F401
