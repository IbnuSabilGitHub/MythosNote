"""LLM prompt templates per generate action."""

from __future__ import annotations

from apps.generate.constants import QUIZ_COUNT_MAP, QUIZ_DIFFICULTY_CHOICES


def _quiz_params(options: dict | None) -> tuple[int, str]:
    options = options or {}
    raw_count = options.get("question_count", "medium")
    if isinstance(raw_count, str):
        count = QUIZ_COUNT_MAP.get(raw_count.lower(), QUIZ_COUNT_MAP["medium"])
    else:
        count = QUIZ_COUNT_MAP.get(raw_count, QUIZ_COUNT_MAP["medium"])

    difficulty = (options.get("difficulty") or "medium").strip().lower()
    if difficulty not in QUIZ_DIFFICULTY_CHOICES:
        difficulty = "medium"
    return count, difficulty


def build_messages(action: str, context_text: str, options: dict | None = None) -> list[dict[str, str]]:
    """Build system + user messages for ChatProvider."""
    options = options or {}

    if action == "summary":
        system = (
            "Anda adalah asisten yang merangkum dokumen. "
            "Buat ringkasan naratif dalam Bahasa Indonesia menggunakan markdown "
            "(paragraf singkat dan/atau bullet points). Jangan tambahkan preamble."
        )
        user = f"Konteks dokumen:\n\n{context_text}\n\nBuat ringkasan eksekutif dari konteks di atas."

    elif action == "table":
        system = (
            "Anda mengekstrak data terstruktur dari dokumen. "
            "Output hanya tabel markdown (header + baris). Bahasa Indonesia. "
            "Tanpa penjelasan di luar tabel."
        )
        user = f"Konteks dokumen:\n\n{context_text}\n\nBuat tabel markdown entitas/konsep kunci."

    elif action == "quiz":
        count, difficulty = _quiz_params(options)
        system = (
            "Anda membuat kuis pilihan ganda dari dokumen. "
            "Output HANYA JSON valid tanpa markdown fence, dengan struktur:\n"
            '{"questions": [{"question": "...", "options": ["A. ...", "B. ...", "C. ...", "D. ..."], '
            '"answer": "A", "explanation": "..."}]}\n'
            f"Buat tepat {count} soal, tingkat kesulitan: {difficulty}. Bahasa Indonesia."
        )
        user = f"Konteks dokumen:\n\n{context_text}\n\nBuat kuis pilihan ganda."

    elif action == "mindmap":
        system = (
            "Anda membuat mind map dari dokumen. "
            "Output HANYA kode Mermaid mindmap (baris pertama: mindmap). "
            "Tanpa penjelasan, tanpa fence markdown."
        )
        user = f"Konteks dokumen:\n\n{context_text}\n\nBuat struktur mindmap Mermaid."

    else:
        raise ValueError(f"Unknown action: {action}")

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
