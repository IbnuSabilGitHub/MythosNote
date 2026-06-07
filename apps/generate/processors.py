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

_DANGEROUS_TAGS_RE = re.compile(
    r"<(/?\s*(?:script|iframe|object|embed|link|style|meta|svg|body|html|head)[^>]*)>|"
    r"\b(?:on(?:load|error|click|mouseover|keydown|submit))\s*=",
    re.IGNORECASE,
)


def _strip_outer_fence(text: str) -> str:
    text = text.strip()
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if match:
        text = match.group(1).strip()
    
    # Ambil PASTI dari { pertama sampai } terakhir
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start:end+1]
        
    return text


def process_output(action: str, raw: str) -> tuple[str | None, str]:
    """Normalize and validate model output. Returns (title, stored_result_string)."""
    raw = (raw or "").strip()
    if not raw:
        raise ProcessOutputError("Model mengembalikan respons kosong.")

    cleaned = _strip_outer_fence(raw)
    
    if _DANGEROUS_TAGS_RE.search(cleaned):
        raise ProcessOutputError("Output ditolak karena terdeteksi mengandung tag HTML/Script berbahaya.")
    
    if action == "summary":
        try:
            data = json.loads(cleaned)
            if isinstance(data, dict):
                return str(data.get("title", "Ringkasan Dokumen")), str(data.get("content", raw))
        except json.JSONDecodeError:
            pass
            
        # Fallback raw markdown if not valid JSON
        content_match = re.search(r'"content"\s*:\s*"(.*?)"(?:\s*\}|,\s*"[^"]+"\s*:|\s*$)', cleaned, re.DOTALL)
        if content_match:
            content_val = content_match.group(1).replace("\\n", "\n").replace('\\"', '"')
            title_match = re.search(r'"title"\s*:\s*"([^"]+)"', cleaned)
            title = title_match.group(1) if title_match else "Ringkasan Dokumen"
            return title, content_val

        lines = cleaned.strip().split("\n", 1)
        title = "Ringkasan Dokumen"
        if lines and lines[0].startswith("#"):
            title = lines[0].strip("# ").strip()
        return title, cleaned
        

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        print(f"FAILED TO DECODE JSON. RAW:\\n{repr(raw)}\\nCLEANED:\\n{repr(cleaned)}")
        raise ProcessOutputError(f"Output {action} bukan JSON valid.") from exc

    if not isinstance(data, dict):
        raise ProcessOutputError(f"Output {action} harus berupa object JSON.")

    title = data.get("title")
    if title and not isinstance(title, str):
        title = str(title)

    content = data.get("content")
    if content is None:
        raise ProcessOutputError(f"Output {action} tidak memiliki field 'content'.")


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
