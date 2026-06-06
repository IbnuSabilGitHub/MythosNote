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


def process_output(action: str, raw: str) -> tuple[str | None, str]:
    """Normalize and validate model output. Returns (title, stored_result_string)."""
    raw = (raw or "").strip()
    if not raw:
        raise ProcessOutputError("Model mengembalikan respons kosong.")

    cleaned = _strip_outer_fence(raw)
    
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ProcessOutputError(f"Output {action} bukan JSON valid.") from exc

    if not isinstance(data, dict):
        raise ProcessOutputError(f"Output {action} harus berupa object JSON.")

    title = data.get("title")
    if title and not isinstance(title, str):
        title = str(title)

    content = data.get("content")
    if content is None:
        raise ProcessOutputError(f"Output {action} tidak memiliki field 'content'.")

    if action == "summary":
        if not isinstance(content, str):
            raise ProcessOutputError("Content summary harus berupa string.")
        return title, content

    if action == "quiz":
        if not isinstance(content, dict) or "questions" not in content:
            raise ProcessOutputError("Content kuis harus berupa object berisi 'questions'.")
            
        questions = content.get("questions")
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

        return title, json.dumps(content, ensure_ascii=False)

    if action in ("table", "mindmap"):
        return title, json.dumps(content, ensure_ascii=False)

    raise ProcessOutputError(f"Action tidak dikenal: {action}")
