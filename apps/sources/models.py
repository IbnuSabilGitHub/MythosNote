import uuid
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from pgvector.django import VectorField


class Source(models.Model):
    """Model untuk menyimpan file sumber yang diupload pengguna."""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('queued', 'Queued'),
        ('processing', 'Processing'),
        ('ready', 'Ready'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sources'
    )
    workspace = models.ForeignKey(
        'workspaces.Workspace',
        on_delete=models.CASCADE,
        related_name='sources'
    )
    original_filename = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=100)
    file_size = models.BigIntegerField()
    storage_path = models.CharField(max_length=500)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    error_message = models.TextField(blank=True, default='')
    extracted_text = models.TextField(blank=True, default='')
    progress = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('workspace', 'original_filename')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['workspace', 'status']),
            models.Index(fields=['user', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.original_filename} ({self.status})"


class SourceChunk(models.Model):
    """Model untuk menyimpan chunks dari file sumber yang sudah diproses."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source = models.ForeignKey(
        Source,
        on_delete=models.CASCADE,
        related_name='chunks'
    )
    chunk_index = models.IntegerField()
    text_content = models.TextField()
    token_count = models.IntegerField()
    embedding = VectorField(dimensions=None, null=True, blank=True)
    metadata = models.JSONField(default=dict)
    
    class Meta:
        unique_together = ('source', 'chunk_index')
        ordering = ['source', 'chunk_index']
        indexes = [
            models.Index(fields=['source', 'chunk_index']),
        ]
    
    def __str__(self):
        return f"Chunk {self.chunk_index} from {self.source.original_filename}"


# ChatSession dan ChatMessage dipindah ke apps.chat.models (refactor 2026-06-06).
