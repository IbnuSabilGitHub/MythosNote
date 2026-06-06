import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class GenerateJob(models.Model):
    """Async generation job for workspace sources."""

    STATUS_CHOICES = [
        ("queued", "Queued"),
        ("processing", "Processing"),
        ("success", "Success"),
        ("failed", "Failed"),
    ]

    ACTION_CHOICES = [
        ("summary", "Summary"),
        ("mindmap", "Mindmap"),
        ("quiz", "Quiz"),
        ("table", "Table"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="generate_jobs",
    )
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="generate_jobs",
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="queued")
    title = models.CharField(max_length=120, blank=True, default="")
    source_ids = models.JSONField(default=list, blank=True)
    options = models.JSONField(default=dict, blank=True)
    result = models.TextField(blank=True, default="")
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sources_generatejob"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["workspace", "status"]),
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self):
        return f"GenerateJob {self.id} ({self.action}, {self.status})"

    def save(self, *args, **kwargs):
        if not self.title and self.action:
            from apps.generate.constants import ACTION_LABELS
            from apps.sources.models import Source

            label = ACTION_LABELS.get(self.action, self.action)
            title_text = label
            
            if getattr(self, "source_ids", None) and isinstance(self.source_ids, list) and len(self.source_ids) > 0:
                try:
                    first_source = Source.objects.filter(id=self.source_ids[0]).first()
                    if first_source:
                        title_text = f"{label} - {first_source.name}"
                        if len(self.source_ids) > 1:
                            title_text += f" (+{len(self.source_ids) - 1} lainnya)"
                except Exception:
                    pass
                    
            if title_text == label:
                stamp = timezone.localtime().strftime("%d %b %Y %H:%M")
                title_text = f"{label} · {stamp}"
                
            self.title = title_text[:120]
        super().save(*args, **kwargs)
