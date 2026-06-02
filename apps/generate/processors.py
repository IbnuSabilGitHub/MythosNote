"""Post-process and validate LLM output per generate action."""

from __future__ import annotations

import json
import re


class ProcessOutputError(Exception):
    """Output validation failed."""


_FENCE_RE = re.compile(r"^```(?:\w+)?\s*\n?(.*?)\n?```\s*$", re.DOTALL)
_MERMAID_FENCE_RE = re.compile(
    r"```mermaid\s*\n?(.*?)\n?```",
    re.DOTALL | re.IGNORECASE,
)


def _strip_outer_fence(text: str) -> str:
    text = text.strip()
    match = _FENCE_RE.match(text)
    if match:
        return match.group(1).strip()
    return text


def process_output(action: str, raw: str) -> str:
    """Normalize and validate model output. Returns stored result string."""
    raw = (raw or "").strip()
    if not raw:
        raise ProcessOutputError("Model mengembalikan respons kosong.")

    if action in ("summary", "table"):
        return _strip_outer_fence(raw)

    if action == "quiz":
        cleaned = _strip_outer_fence(raw)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ProcessOutputError("Output kuis bukan JSON valid.") from exc

        questions = data.get("questions")
        if not isinstance(questions, list) or len(questions) == 0:
            raise ProcessOutputError("JSON kuis harus berisi array 'questions'.")

        for idx, item in enumerate(questions):
            if not isinstance(item, dict):
                raise ProcessOutputError(f"Pertanyaan #{idx + 1} tidak valid.")
            for key in ("question", "options", "answer"):
                if key not in item:
                    raise ProcessOutputError(f"Pertanyaan #{idx + 1} kurang field '{key}'.")
            if not isinstance(item["options"], list) or len(item["options"]) < 2:
                raise ProcessOutputError(f"Pertanyaan #{idx + 1} butuh minimal 2 opsi.")

        return json.dumps(data, ensure_ascii=False)

    if action == "mindmap":
        text = raw
        mermaid_match = _MERMAID_FENCE_RE.search(text)
        if mermaid_match:
            text = mermaid_match.group(1).strip()
        else:
            text = _strip_outer_fence(text)

        if not text.lower().startswith("mindmap"):
            raise ProcessOutputError("Mindmap harus diawali dengan 'mindmap'.")
        return text

    raise ProcessOutputError(f"Action tidak dikenal: {action}")
