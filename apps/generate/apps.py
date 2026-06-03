"""App config untuk generate."""

from django.apps import AppConfig


class GenerateConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.generate"
    verbose_name = "Generate"
