# Generated manually for the initial MythosNote auth foundation.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("email_verified", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="profile",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="UserUsage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("identifier", models.CharField(blank=True, max_length=255)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("date", models.DateField()),
                ("prompt_count", models.PositiveIntegerField(default=0)),
                ("generate_count", models.PositiveIntegerField(default=0)),
                ("failed_login_count", models.PositiveIntegerField(default=0)),
                ("failed_login_window_started_at", models.DateTimeField(blank=True, null=True)),
                ("last_failed_login_at", models.DateTimeField(blank=True, null=True)),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="usage_records",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(fields=["date", "identifier"], name="accounts_us_date_d337ac_idx"),
                    models.Index(fields=["date", "user"], name="accounts_us_date_db1c92_idx"),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("user", "identifier", "date"),
                        name="unique_user_usage_per_identifier_day",
                    ),
                ],
            },
        ),
    ]
