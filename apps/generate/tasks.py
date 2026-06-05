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

    except Exception as exc:
        error_traceback = traceback.format_exc()
        print(f"ERROR processing generate job {job_id}: {error_traceback}")

        if job is not None:
            with transaction.atomic():
                job = GenerateJob.objects.select_for_update().get(id=job.id)
                job.status = "failed"
                
                exc_str = str(exc)
                if "503" in exc_str or "experiencing high demand" in exc_str.lower() or "429" in exc_str or "quota" in exc_str.lower():
                    user_msg = "Layanan sedang padat. Silakan coba beberapa saat lagi."
                elif "timeout" in exc_str.lower() or "deadline" in exc_str.lower():
                    user_msg = "Koneksi terputus. Silakan coba lagi."
                elif "403" in exc_str or "api key" in exc_str.lower() or "500" in exc_str:
                    user_msg = "Terjadi gangguan sistem."
                else:
                    user_msg = "Terjadi kesalahan saat memproses data."
                
                job.error_message = user_msg[:500]
                job.save(update_fields=["status", "error_message", "updated_at"])
