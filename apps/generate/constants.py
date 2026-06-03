"""Shared constants for generate feature."""

MAX_GENERATE_CHARS = 12_000
MAX_GENERATE_CHUNKS = 200

ACTION_LABELS = {
    "summary": "Ringkasan",
    "mindmap": "Mindmap",
    "quiz": "Quiz",
    "table": "Tabel",
}

QUIZ_COUNT_MAP = {
    "few": 5,
    "medium": 10,
    "many": 20,
    5: 5,
    10: 10,
    20: 20,
}

QUIZ_DIFFICULTY_CHOICES = ("easy", "medium", "hard")
