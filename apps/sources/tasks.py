"""Tasks untuk memproses source files."""

import rq
from django.conf import settings
from apps.sources.models import Source


def process_source(source_id: str) -> None:
    """Task RQ untuk memproses file source.

    Args:
        source_id: UUID dari objek Source yang akan diproses.
    """
    try:
        source = Source.objects.get(id=source_id)
        source.status = 'processing'
        source.save(update_fields=['status', 'updated_at'])

        # TODO: Implementasi pemrosesan file (parsing, chunking, embedding)
        # Untuk saat ini, hanya update status ke ready
        source.status = 'ready'
        source.progress = 100
        source.save(update_fields=['status', 'progress', 'updated_at'])

    except Source.DoesNotExist:
        # Source tidak ditemukan, log error jika perlu
        pass
    except Exception as e:
        # Handle error dan update status ke failed
        if 'source' in locals():
            source.status = 'failed'
            source.error_message = str(e)
            source.save(update_fields=['status', 'error_message', 'updated_at'])