"""Serializers for generate API."""

from rest_framework import serializers

from apps.generate.constants import QUIZ_COUNT_MAP, QUIZ_DIFFICULTY_CHOICES
from apps.generate.models import GenerateJob


VALID_ACTIONS = {choice[0] for choice in GenerateJob.ACTION_CHOICES}


class GenerateCreateSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=sorted(VALID_ACTIONS))
    source_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False,
    )
    options = serializers.DictField(required=False, default=dict)

    def validate(self, attrs):
        action = attrs.get("action")
        options = dict(attrs.get("options") or {})
        if action == "quiz" and options:
            raw_count = options.get("question_count", "medium")
            if isinstance(raw_count, str):
                if raw_count.lower() not in QUIZ_COUNT_MAP:
                    raise serializers.ValidationError(
                        {
                            "options": {
                                "question_count": (
                                    "Harus few, medium, many, atau 5/10/20."
                                )
                            }
                        }
                    )
            elif raw_count not in (5, 10, 20):
                raise serializers.ValidationError(
                    {
                        "options": {
                            "question_count": "Harus 5, 10, 20, atau few/medium/many."
                        }
                    }
                )

            difficulty = (options.get("difficulty") or "medium").strip().lower()
            if difficulty not in QUIZ_DIFFICULTY_CHOICES:
                raise serializers.ValidationError(
                    {"options": {"difficulty": "Harus easy, medium, atau hard."}}
                )
            options["difficulty"] = difficulty

        attrs["options"] = options
        return attrs


class GenerateJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = GenerateJob
        fields = [
            "id",
            "action",
            "status",
            "title",
            "source_ids",
            "options",
            "result",
            "error_message",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class GenerateJobCreatedSerializer(serializers.ModelSerializer):
    class Meta:
        model = GenerateJob
        fields = ["id", "action", "status", "title", "created_at"]
        read_only_fields = fields
