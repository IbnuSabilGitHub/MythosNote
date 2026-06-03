# State-only: adopt existing sources_generatejob table

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("sources", "0004_remove_generatejob_state"),
        ("workspaces", "__first__"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="GenerateJob",
                    fields=[
                        (
                            "id",
                            models.UUIDField(
                                default=uuid.uuid4,
                                editable=False,
                                primary_key=True,
                                serialize=False,
                            ),
                        ),
                        (
                            "action",
                            models.CharField(
                                choices=[
                                    ("summary", "Summary"),
                                    ("mindmap", "Mindmap"),
                                    ("quiz", "Quiz"),
                                    ("table", "Table"),
                                ],
                                max_length=20,
                            ),
                        ),
                        (
                            "status",
                            models.CharField(
                                choices=[
                                    ("queued", "Queued"),
                                    ("processing", "Processing"),
                                    ("success", "Success"),
                                    ("failed", "Failed"),
                                ],
                                default="queued",
                                max_length=20,
                            ),
                        ),
                        ("result", models.TextField(blank=True, default="")),
                        ("error_message", models.TextField(blank=True, default="")),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                        ("updated_at", models.DateTimeField(auto_now=True)),
                        (
                            "user",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="generate_jobs",
                                to=settings.AUTH_USER_MODEL,
                            ),
                        ),
                        (
                            "workspace",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="generate_jobs",
                                to="workspaces.workspace",
                            ),
                        ),
                    ],
                    options={
                        "db_table": "sources_generatejob",
                        "ordering": ["-created_at"],
                        "indexes": [
                            models.Index(
                                fields=["workspace", "status"],
                                name="sources_gen_workspa_065df3_idx",
                            ),
                            models.Index(
                                fields=["user", "created_at"],
                                name="sources_gen_user_id_ced6e3_idx",
                            ),
                        ],
                    },
                ),
            ],
            database_operations=[],
        ),
    ]
