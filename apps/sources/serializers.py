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


class SourceListSerializer(serializers.ModelSerializer):
    """Serializer ringkas untuk daftar Source."""

    class Meta:
        model = Source
        fields = [
            'id',
            'workspace',
            'original_filename',
            'mime_type',
            'file_size',
            'status',
            'progress',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


class SourceStatusSerializer(serializers.Serializer):
    """Serializer status source beserta ringkasan chunk."""

    id = serializers.UUIDField()
    status = serializers.ChoiceField(choices=Source.STATUS_CHOICES)
    progress = serializers.IntegerField()
    total_chunks = serializers.IntegerField()
    successful_chunks = serializers.IntegerField()
    failed_chunks = serializers.IntegerField()
    error_message = serializers.CharField(allow_blank=True)