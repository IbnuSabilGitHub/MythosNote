"""Tasks untuk memproses source files."""

import os
import re
import tempfile
import traceback
from contextlib import contextmanager
from typing import List

import fitz  # PyMuPDF
from django.db import transaction
from django.utils import timezone

from apps.sources.embeddings import EmbeddingProvider
from apps.sources.models import GenerateJob, Source, SourceChunk
from apps.sources.providers import ChatProvider
from apps.sources.utils import download_source_from_supabase


def normalize_text(text: str) -> str:
    """Normalisasi teks dengan menghapus whitespace ganda."""
    # Replace multiple whitespace (including newlines, tabs) with single space
    text = re.sub(r'\s+', ' ', text)
    # Strip leading/trailing whitespace
    text = text.strip()
    return text


def count_tokens_approx(text: str) -> int:
    """Hitung perkiraan jumlah token dalam teks."""
    return max(1, len(text) // 4)


def chunk_text(text: str, max_tokens: int = 500, overlap: int = 50) -> List[str]:
    """Memecah teks menjadi chunks berdasarkan paragraf dan kata."""
    if not text or not text.strip():
        return []

    # Split into paragraphs (by double newline or multiple newlines)
    paragraphs = re.split(r'\n\s*\n', text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    chunks = []

    for paragraph in paragraphs:
        para_tokens = count_tokens_approx(paragraph)

        if para_tokens <= max_tokens:
            # Paragraf cukup kecil, tambahkan langsung
            chunks.append(paragraph)
        else:
            # Paragraf terlalu besar, split per kalimat
            sentences = re.split(r'(?<=[.!?])\s+', paragraph)
            sentences = [s.strip() for s in sentences if s.strip()]

            current_chunk = ""
            current_tokens = 0

            for sentence in sentences:
                sent_tokens = count_tokens_approx(sentence)

                if sent_tokens > max_tokens:
                    # Kalimat terlalu besar, split per kata
                    words = sentence.split()
                    word_chunk = []
                    word_tokens = 0

                    for word in words:
                        w_tokens = count_tokens_approx(word)
                        if word_tokens + w_tokens > max_tokens:
                            # Simpan chunk kata yang ada
                            if word_chunk:
                                chunks.append(' '.join(word_chunk))
                            word_chunk = [word]
                            word_tokens = w_tokens
                        else:
                            word_chunk.append(word)
                            word_tokens += w_tokens

                    if word_chunk:
                        chunks.append(' '.join(word_chunk))

                elif current_tokens + sent_tokens > max_tokens:
                    # Simpan chunk saat ini dan mulai baru
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = sentence
                    current_tokens = sent_tokens
                else:
                    # Tambahkan kalimat ke chunk saat ini
                    if current_chunk:
                        current_chunk += ' ' + sentence
                    else:
                        current_chunk = sentence
                    current_tokens += sent_tokens

            # Simpan chunk terakhir dari paragraf ini
            if current_chunk:
                chunks.append(current_chunk)

    # Apply overlap if needed and possible
    if overlap > 0 and len(chunks) > 1:
        overlapped_chunks = []
        for i, chunk in enumerate(chunks):
            if i == 0:
                overlapped_chunks.append(chunk)
            else:
                # Get overlap from previous chunk
                prev_chunk = overlapped_chunks[-1] if not overlapped_chunks else chunks[i-1]
                prev_tokens = count_tokens_approx(prev_chunk)

                if prev_tokens > overlap:
                    # Extract last portion of previous chunk for overlap
                    # Simple approach: take last N characters that approximate overlap tokens
                    overlap_chars = overlap * 4  # ~4 chars per token
                    overlap_text = prev_chunk[-overlap_chars:] if len(prev_chunk) > overlap_chars else prev_chunk

                    # Find word boundary
                    space_idx = overlap_text.find(' ')
                    if space_idx > 0:
                        overlap_text = overlap_text[space_idx:].strip()

                    if overlap_text:
                        chunk = overlap_text + ' ' + chunk

                overlapped_chunks.append(chunk)

        chunks = overlapped_chunks

    return chunks


def extract_text_from_file(file_path: str, mime_type: str) -> str:
    """Ekstrak teks dari file berdasarkan tipe MIME.

    Args:
        file_path: Path ke file di storage.
        mime_type: Tipe MIME file.

    Returns:
        Teks yang diekstrak dari file.

    Raises:
        ValueError: Jika format file tidak didukung.
    """
    # Normalize mime_type (handle variations like 'application/pdf' vs 'PDF')
    mime_lower = mime_type.lower()

    # Check file extension as fallback
    _, ext = os.path.splitext(file_path)
    ext_lower = ext.lower()

    is_pdf = mime_lower == 'application/pdf' or ext_lower == '.pdf'
    is_md = mime_lower in ('text/markdown', 'text/x-markdown') or ext_lower == '.md'
    is_txt = mime_lower.startswith('text/plain') or ext_lower == '.txt'

    if is_pdf:
        # Extract text from PDF using PyMuPDF
        try:
            doc = fitz.open(file_path)
            text_parts = []
            for page in doc:
                text_parts.append(page.get_text())
            doc.close()
            return '\n'.join(text_parts)
        except Exception as e:
            raise ValueError(f"Error membaca PDF: {str(e)}")

    elif is_md or is_txt:
        # Read markdown or plain text directly
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with latin-1 encoding as fallback
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    return f.read()
            except Exception as e:
                raise ValueError(f"Error membaca file teks: {str(e)}")
        except Exception as e:
            raise ValueError(f"Error membaca file teks: {str(e)}")

    else:
        # Format tidak dikenali
        raise ValueError(f"Format file tidak didukung: {mime_type} (extension: {ext})")


@contextmanager
def source_file_path(storage_path: str):
    """Yield a local temp file path downloaded from Supabase Storage."""

    _, extension = os.path.splitext(storage_path)
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=extension)
    temp_name = temp_file.name

    try:
        with temp_file:
            temp_file.write(download_source_from_supabase(storage_path))
        yield temp_name
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def process_source(source_id: str) -> None:
    """Task RQ untuk memproses file source."""
    source = None
    try:
        with transaction.atomic():
            source = Source.objects.select_for_update().get(id=source_id)
            if source.status != 'pending':
                return

            source.status = 'processing'
            source.progress = 0
            source.error_message = ''
            source.save(update_fields=['status', 'progress', 'error_message', 'updated_at'])
            source.chunks.all().delete()

        with source_file_path(source.storage_path) as file_path:
            if not os.path.exists(file_path):
                raise ValueError(f"File tidak ditemukan di storage: {source.storage_path}")
            raw_text = extract_text_from_file(file_path, source.mime_type)

        if not raw_text or not raw_text.strip():
            raise ValueError("File kosong atau tidak mengandung teks yang dapat diekstrak")

        normalized_text = normalize_text(raw_text)
        chunks = chunk_text(normalized_text, max_tokens=500, overlap=50)

        if not chunks:
            raise ValueError("Tidak ada chunks yang dihasilkan dari teks")

        total_chunks = len(chunks)
        processed_chunks = 0

        for idx, chunk_text_content in enumerate(chunks):
            embedding = EmbeddingProvider.get_embedding(chunk_text_content)

            SourceChunk.objects.create(
                source=source,
                chunk_index=idx,
                text_content=chunk_text_content,
                token_count=count_tokens_approx(chunk_text_content),
                embedding=embedding,
                metadata={'status': 'ready'},
            )

            processed_chunks += 1
            progress_percentage = int((processed_chunks / total_chunks) * 100)
            Source.objects.filter(id=source.id, status='processing').update(
                progress=progress_percentage,
                updated_at=timezone.now(),
            )

        with transaction.atomic():
            source = Source.objects.select_for_update().get(id=source_id)
            source.status = 'ready'
            source.progress = 100
            source.error_message = ''
            source.save(update_fields=['status', 'progress', 'error_message', 'updated_at'])

    except Source.DoesNotExist:
        # Source tidak ditemukan
        error_msg = f"Source dengan ID {source_id} tidak ditemukan"
        print(f"ERROR: {error_msg}")
        # Tidak bisa update database karena source tidak ada

    except Exception as e:
        # Tangkap exception, set status='failed' dengan traceback
        error_traceback = traceback.format_exc()
        print(f"ERROR processing source {source_id}: {error_traceback}")

        if source is not None:
            with transaction.atomic():
                source = Source.objects.select_for_update().get(id=source.id)
                source.status = 'failed'
                source.error_message = error_traceback
                source.save(update_fields=['status', 'error_message', 'updated_at'])

        # Jangan hapus file mentah - file tetap di storage


def process_generate_job(job_id: str, prompt: str) -> None:
    """Async task to run generation prompt against workspace context."""
    job = None
    try:
        with transaction.atomic():
            job = GenerateJob.objects.select_for_update().get(id=job_id)
            if job.status != "queued":
                return
            job.status = "processing"
            job.error_message = ""
            job.save(update_fields=["status", "error_message", "updated_at"])

        response_text = ChatProvider.chat_complete(
            messages=[{"role": "user", "content": prompt}],
        )

        with transaction.atomic():
            job = GenerateJob.objects.select_for_update().get(id=job_id)
            job.status = "success"
            job.result = response_text or ""
            job.error_message = ""
            job.save(update_fields=["status", "result", "error_message", "updated_at"])

    except GenerateJob.DoesNotExist:
        error_msg = f"GenerateJob dengan ID {job_id} tidak ditemukan"
        print(f"ERROR: {error_msg}")

    except Exception:
        error_traceback = traceback.format_exc()
        print(f"ERROR processing generate job {job_id}: {error_traceback}")

        if job is not None:
            with transaction.atomic():
                job = GenerateJob.objects.select_for_update().get(id=job.id)
                job.status = "failed"
                job.error_message = error_traceback
                job.save(update_fields=["status", "error_message", "updated_at"])


if __name__ == '__main__':
    """Guard untuk testing standalone."""
    import sys
    import django

    # Setup Django untuk running standalone
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()

    if len(sys.argv) < 2:
        print("Usage: python tasks.py <source_id>")
        print("Example: python tasks.py 550e8400-e29b-41d4-a716-446655440000")
        sys.exit(1)

    source_uuid = sys.argv[1]
    print(f"Processing source: {source_uuid}")
    process_source(source_uuid)
    print("Done!")
