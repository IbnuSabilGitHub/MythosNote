"""Serializers untuk app sources."""

from rest_framework import serializers
from apps.sources.models import Source


class SourceSerializer(serializers.ModelSerializer):
    """Serializer untuk model Source."""

    class Meta:
        model = Source
        fields = [
            'id',
            'user',
            'workspace',
            'original_filename',
            'mime_type',
            'file_size',
            'storage_path',
            'status',
            'error_message',
            'progress',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'user',
            'workspace',
            'original_filename',
            'mime_type',
            'file_size',
            'storage_path',
            'status',
            'error_message',
            'progress',
            'created_at',
            'updated_at',
        ]