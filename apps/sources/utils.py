"""Utilities for Supabase storage integration."""

from __future__ import annotations

import os
from typing import BinaryIO

from supabase import Client, create_client


def _get_supabase_env() -> tuple[str, str, str]:
    url = os.getenv('SUPABASE_URL', '').strip()
    key = os.getenv('SUPABASE_KEY', '').strip()
    bucket = os.getenv('SUPABASE_BUCKET', '').strip()

    if not url or not key or not bucket:
        raise ValueError('SUPABASE_URL, SUPABASE_KEY, dan SUPABASE_BUCKET wajib diisi.')

    return url, key, bucket


def get_supabase_client() -> tuple[Client, str]:
    """Create a Supabase client and return it with configured bucket name."""

    url, key, bucket = _get_supabase_env()
    return create_client(url, key), bucket


def upload_source_to_supabase(file_obj: BinaryIO, storage_path: str, content_type: str | None = None) -> str:
    """Upload file object to Supabase Storage and return persisted storage path."""

    client, bucket = get_supabase_client()
    content = file_obj.read()
    file_options = {
        'content-type': content_type or 'application/octet-stream',
        'upsert': 'false',
    }

    # Use Supabase storage upload API with configured bucket.
    client.storage.from_(bucket).upload(path=storage_path, file=content, file_options=file_options)
    return storage_path


def download_source_from_supabase(storage_path: str) -> bytes:
    """Download source bytes from Supabase Storage by storage path."""

    client, bucket = get_supabase_client()
    return client.storage.from_(bucket).download(storage_path)


def delete_source_from_supabase(storage_path: str) -> None:
    """Delete source file from Supabase Storage if storage path is present."""

    if not storage_path:
        return

    client, bucket = get_supabase_client()
    client.storage.from_(bucket).remove([storage_path])