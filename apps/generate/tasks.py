"""RQ background tasks for generate jobs."""

import traceback

from django.db import transaction

from apps.generate.models import GenerateJob
from apps.generate.processors import ProcessOutputError, process_output
from apps.generate.prompts import build_messages
from apps.generate.services import GenerateContextError, get_generate_context
from apps.sources.providers import ChatProvider


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
        processed = process_output(job.action, response_text or "")

        with transaction.atomic():
            job = GenerateJob.objects.select_for_update().get(id=job_id)
            job.status = "success"
            job.result = processed
            job.error_message = ""
            job.save(update_fields=["status", "result", "error_message", "updated_at"])

    except GenerateJob.DoesNotExist:
        print(f"ERROR: GenerateJob {job_id} tidak ditemukan")

    except (GenerateContextError, ProcessOutputError) as exc:
        if job is not None:
            with transaction.atomic():
                job = GenerateJob.objects.select_for_update().get(id=job.id)
                job.status = "failed"
                job.error_message = str(exc)[:500]
                job.save(update_fields=["status", "error_message", "updated_at"])

    except Exception:
        error_traceback = traceback.format_exc()
        print(f"ERROR processing generate job {job_id}: {error_traceback}")

        if job is not None:
            with transaction.atomic():
                job = GenerateJob.objects.select_for_update().get(id=job.id)
                job.status = "failed"
                short_error = error_traceback[:500] if error_traceback else (
                    "Terjadi kesalahan saat memproses."
                )
                job.error_message = short_error
                job.save(update_fields=["status", "error_message", "updated_at"])
