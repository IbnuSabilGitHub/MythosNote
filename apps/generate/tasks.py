"""RQ background tasks for generate jobs."""

import logging
import traceback

from django.db import transaction

from apps.generate.models import GenerateJob
from apps.generate.processors import ProcessOutputError, process_output
from apps.generate.prompts import build_messages
from apps.generate.services import GenerateContextError, get_generate_context
from apps.core.providers import ChatProvider

logger = logging.getLogger(__name__)


# Error strings yang menandakan masalah di sisi provider eksternal
_PROVIDER_OVERLOAD_HINTS = ("503", "experiencing high demand", "429", "quota")
_PROVIDER_TIMEOUT_HINTS = ("timeout", "deadline")
_PROVIDER_AUTH_HINTS = ("403", "api key", "500")


def _classify_error_message(exc: Exception) -> str:
    """Terjemahkan exception provider ke pesan user-friendly."""
    exc_str = str(exc).lower()
    if any(hint in exc_str for hint in _PROVIDER_OVERLOAD_HINTS):
        return "Layanan sedang padat. Silakan coba beberapa saat lagi."
    if any(hint in exc_str for hint in _PROVIDER_TIMEOUT_HINTS):
        return "Koneksi terputus. Silakan coba lagi."
    if any(hint in exc_str for hint in _PROVIDER_AUTH_HINTS):
        return "Terjadi gangguan sistem."
    return "Terjadi kesalahan saat memproses data."


def _mark_job_failed(job_id: str, message: str) -> None:
    """Set status job menjadi failed dengan pesan error."""
    with transaction.atomic():
        job = GenerateJob.objects.select_for_update().get(id=job_id)
        job.status = "failed"
        job.error_message = message[:500]
        job.save(update_fields=["status", "error_message", "updated_at"])


def process_generate_job(job_id: str) -> None:
    """Run generation for a queued job."""
    job = None
    try:
        with transaction.atomic():
            job = GenerateJob.objects.select_for_update().get(id=job_id)
            if job.status != "queued":
                return
            job.status = "processing"
            job.error_message = ""
            job.save(update_fields=["status", "error_message", "updated_at"])

        context_text, _ = get_generate_context(
            user=job.user,
            workspace_id=job.workspace_id,
            source_ids=job.source_ids,
        )
        messages = build_messages(job.action, context_text, job.options)
        response_text = ChatProvider.chat_complete(messages=messages)
        title, processed = process_output(job.action, response_text or "")

        with transaction.atomic():
            job = GenerateJob.objects.select_for_update().get(id=job_id)
            job.status = "success"
            job.result = processed
            if title:
                job.title = title[:120]
            job.error_message = ""
            job.save(update_fields=["status", "result", "title", "error_message", "updated_at"])

    except GenerateJob.DoesNotExist:
        logger.error("GenerateJob %s tidak ditemukan.", job_id)

    except (GenerateContextError, ProcessOutputError) as exc:
        if job is not None:
            _mark_job_failed(job.id, str(exc))

    except Exception as exc:
        logger.error("ERROR processing generate job %s:\n%s", job_id, traceback.format_exc())
        if job is not None:
            _mark_job_failed(job.id, _classify_error_message(exc))
