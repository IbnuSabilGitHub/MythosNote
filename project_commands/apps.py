"""Konfigurasi app untuk command manajemen proyek."""

from django.apps import AppConfig


class ProjectCommandsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "project_commands"
