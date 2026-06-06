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
            "Anda adalah asisten ahli yang merangkum dokumen. "
            "Output HANYA JSON valid tanpa markdown fence dengan struktur:\n"
            '{"title": "Judul Singkat Menarik", "content": "Ringkasan markdown terstruktur..."}\n'
            "Isi content WAJIB menggunakan format Markdown yang kaya:\n"
            "- Gunakan **teks tebal** untuk kata kunci/istilah penting.\n"
            "- Gunakan *bullet points* untuk menjabarkan daftar atau poin utama.\n"
            "- Pisahkan antar paragraf dengan newline ganda (\\n\\n).\n"
            "Pastikan JSON valid. Tanpa penjelasan."
        )
        user = f"Konteks dokumen:\n\n{context_text}\n\nBuat ringkasan eksekutif dari konteks di atas beserta judul yang merangkum semua sumber."

    elif action == "table":
        system = (
            "Anda mengekstrak data terstruktur dari dokumen. "
            "Output HANYA JSON valid tanpa markdown fence dengan struktur:\n"
            '{"title": "Judul Tabel", "content": [{"Sumber": "Nama File", "Topik": "Nilai1", "Deskripsi": "Nilai2"}]}\n'
            "Sertakan kolom 'Sumber' untuk mengidentifikasi dari dokumen mana baris data tersebut berasal. "
            "Bahasa Indonesia. Tanpa penjelasan di luar JSON."
        )
        user = f"Konteks dokumen:\n\n{context_text}\n\nBuat tabel data entitas/konsep kunci dalam format JSON beserta judulnya."

    elif action == "quiz":
        count, difficulty = _quiz_params(options)
        system = (
            "Anda membuat kuis pilihan ganda dari dokumen. "
            "Output HANYA JSON valid tanpa markdown fence dengan struktur:\n"
            '{"title": "Judul Kuis", "content": {"questions": [{"question": "...", "options": ["A. ...", "B. ..."], "answer": "A", "explanation": "..."}]}}\n'
            f"Buat tepat {count} soal, tingkat kesulitan: {difficulty}. Bahasa Indonesia."
        )
        user = f"Konteks dokumen:\n\n{context_text}\n\nBuat kuis pilihan ganda beserta judul kuis yang mewakili materi."

    elif action == "mindmap":
        system = (
            "Anda membuat hirarki dokumen. "
            "Output HANYA JSON valid tanpa markdown fence dengan struktur:\n"
            '{"title": "Judul Mindmap", "content": {"name": "Root Topik", "children": [{"name": "Subtopik 1", "children": []}]}}\n'
            "Batasi maksimal 4 tingkat kedalaman. Tanpa penjelasan."
        )
        user = f"Konteks dokumen:\n\n{context_text}\n\nBuat struktur hirarki JSON beserta judul utama yang merangkum keseluruhan."

    else:
        raise ValueError(f"Unknown action: {action}")

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
