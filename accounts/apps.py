"""Konfigurasi aplikasi untuk app accounts."""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Daftarkan model akun dan hook signal untuk status auth."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"

    def ready(self) -> None:
        """Muat handler signal saat registry app siap."""

        import accounts.signals  # noqa: F401
