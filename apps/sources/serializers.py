"""Serializers for source management APIs."""

from rest_framework import serializers

from apps.sources.models import Source


class SourceListSerializer(serializers.ModelSerializer):
    """Compact source representation for workspace lists."""

    file_name = serializers.CharField(source="original_filename", read_only=True)

    class Meta:
        model = Source
        fields = ["id", "file_name", "status", "created_at", "file_size", "progress", "error_message"]
        read_only_fields = fields


class SourceDetailSerializer(SourceListSerializer):
    """Detailed source representation for upload and polling responses."""

    chunk_count = serializers.IntegerField(source="chunks.count", read_only=True)

    class Meta(SourceListSerializer.Meta):
        fields = SourceListSerializer.Meta.fields + [
            "chunk_count",
        ]
        read_only_fields = fields

