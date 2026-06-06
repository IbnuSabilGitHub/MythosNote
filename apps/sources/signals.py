"""Signals for source file cleanup on deletion."""

import logging

from django.core.files.storage import default_storage
from django.db.models.signals import post_delete
from django.dispatch import receiver

from apps.sources.models import Source


logger = logging.getLogger(__name__)


@receiver(post_delete, sender=Source)
def cleanup_source_storage(sender, instance, **kwargs):
    """Delete the stored file when a Source record is deleted.

    This handles cascade deletes (e.g. workspace deletion) ensuring
    orphaned files are removed from storage.
    """
    storage_path = instance.storage_path
    if not storage_path:
        return

    try:
        if default_storage.exists(storage_path):
            default_storage.delete(storage_path)
    except Exception:
        logger.warning(
            "Failed to delete storage file %s for source %s",
            storage_path,
            instance.id,
            exc_info=True,
        )
