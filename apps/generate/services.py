"""Build generation context from selected workspace sources."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from django.shortcuts import get_object_or_404

from apps.generate.constants import MAX_GENERATE_CHARS, MAX_GENERATE_CHUNKS
from apps.sources.models import SourceChunk
from apps.workspaces.models import Workspace


class GenerateContextError(Exception):
    """Validation error when building generate context."""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _normalize_source_ids(source_ids: Any) -> list[str]:
    if not isinstance(source_ids, list) or len(source_ids) == 0:
        raise GenerateContextError("Harap pilih setidaknya satu dokumen untuk generate.")

    normalized: list[str] = []
    for raw in source_ids:
        try:
            normalized.append(str(UUID(str(raw))))
        except (TypeError, ValueError) as exc:
            raise GenerateContextError("source_ids berisi UUID tidak valid.") from exc
    return normalized


def get_generate_context(
    *,
    user,
    workspace_id,
    source_ids: list,
) -> tuple[str, list[dict]]:
    """Return context text and source metadata snapshots for selected sources."""
    normalized_ids = _normalize_source_ids(source_ids)

    workspace = get_object_or_404(
        Workspace.objects.filter(user=user),
        id=workspace_id,
    )

    chunks_qs = (
        SourceChunk.objects.filter(
            source__workspace=workspace,
            source__user=user,
            source__status="ready",
            source_id__in=normalized_ids,
        )
        .select_related("source")
        .order_by("source_id", "chunk_index")[:MAX_GENERATE_CHUNKS]
    )

    if not chunks_qs.exists():
        raise GenerateContextError(
            "Dokumen yang dipilih tidak memiliki konteks yang siap."
        )

    context_parts: list[str] = []
    source_snapshots: list[dict] = []
    seen_source_ids: set[str] = set()
    total_chars = 0

    for chunk in chunks_qs:
        source_obj = chunk.source
        sid = str(source_obj.id)
        if sid not in seen_source_ids:
            seen_source_ids.add(sid)
            source_snapshots.append(
                {
                    "id": sid,
                    "original_filename": source_obj.original_filename,
                }
            )

        part = f"[{source_obj.original_filename}]: {chunk.text_content}"
        if total_chars + len(part) > MAX_GENERATE_CHARS:
            break
        context_parts.append(part)
        total_chars += len(part)

    if not context_parts:
        raise GenerateContextError(
            "Dokumen yang dipilih tidak memiliki konteks yang siap."
        )

    return "\n\n".join(context_parts), source_snapshots
