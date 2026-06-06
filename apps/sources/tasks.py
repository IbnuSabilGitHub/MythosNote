"""Tasks untuk memproses source files."""

import os
import re
import tempfile
import traceback
from contextlib import contextmanager

import fitz  # PyMuPDF
from django.core.files.storage import default_storage
from django.db import transaction
from django.utils import timezone

from apps.sources.embeddings import EmbeddingProvider
from apps.sources.models import Source, SourceChunk


# ── Batas ekstraksi ──────────────────────────────────────────────────────────
MAX_EXTRACT_PAGES = 500
MAX_EXTRACTED_CHARS = 2_000_000


def normalize_text(text: str) -> str:
    """Normalisasi teks dengan menghapus whitespace ganda."""
    return re.sub(r'\s+', ' ', text).strip()


def count_tokens_approx(text: str) -> int:
    """Hitung perkiraan jumlah token dalam teks."""
    return max(1, len(text) // 4)


def chunk_text(text: str, max_tokens: int = 500, overlap: int = 50) -> list[str]:
    """Memecah teks menjadi chunks berdasarkan paragraf dan kata."""
    if not text or not text.strip():
        return []

    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
    chunks = []

    for paragraph in paragraphs:
        para_tokens = count_tokens_approx(paragraph)

        if para_tokens <= max_tokens:
            chunks.append(paragraph)
        else:
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', paragraph) if s.strip()]
            current_chunk = ""
            current_tokens = 0

            for sentence in sentences:
                sent_tokens = count_tokens_approx(sentence)

                if sent_tokens > max_tokens:
                    words = sentence.split()
                    word_chunk: list[str] = []
                    word_tokens = 0

                    for word in words:
                        w_tokens = count_tokens_approx(word)
                        if word_tokens + w_tokens > max_tokens:
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
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = sentence
                    current_tokens = sent_tokens
                else:
                    current_chunk = (current_chunk + ' ' + sentence).strip() if current_chunk else sentence
                    current_tokens += sent_tokens

            if current_chunk:
                chunks.append(current_chunk)

    # Apply overlap
    if overlap > 0 and len(chunks) > 1:
        overlapped_chunks = [chunks[0]]
        for i in range(1, len(chunks)):
            prev_chunk = chunks[i - 1]
            prev_tokens = count_tokens_approx(prev_chunk)

            if prev_tokens > overlap:
                overlap_chars = overlap * 4
                overlap_text = prev_chunk[-overlap_chars:] if len(prev_chunk) > overlap_chars else prev_chunk
                space_idx = overlap_text.find(' ')
                if space_idx > 0:
                    overlap_text = overlap_text[space_idx:].strip()
                if overlap_text:
                    chunks[i] = overlap_text + ' ' + chunks[i]

            overlapped_chunks.append(chunks[i])
        chunks = overlapped_chunks

    return chunks


def _extract_pdf(file_path: str) -> str:
    """Ekstrak teks dari file PDF."""
    try:
        doc = fitz.open(file_path)
        if doc.page_count > MAX_EXTRACT_PAGES:
            doc.close()
            raise ValueError(
                f"PDF terlalu banyak halaman ({doc.page_count}). "
                f"Maksimal {MAX_EXTRACT_PAGES} halaman."
            )
        text_parts = []
        total_chars = 0
        for page in doc:
            page_text = page.get_text()
            total_chars += len(page_text)
            if total_chars > MAX_EXTRACTED_CHARS:
                text_parts.append(page_text[:MAX_EXTRACTED_CHARS - (total_chars - len(page_text))])
                break
            text_parts.append(page_text)
        doc.close()
        return '\n'.join(text_parts)
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Error membaca PDF: {e}")


def _extract_docx(file_path: str) -> str:
    """Ekstrak teks dari file DOCX."""
    try:
        from docx import Document
        doc = Document(file_path)
        text_parts = []
        total_chars = 0
        for p in doc.paragraphs:
            if p.text.strip():
                total_chars += len(p.text)
                if total_chars > MAX_EXTRACTED_CHARS:
                    break
                text_parts.append(p.text)
        return '\n'.join(text_parts)
    except Exception as e:
        raise ValueError(f"Error membaca DOCX: {e}")


def _extract_text_file(file_path: str) -> str:
    """Baca file teks (MD / TXT) dengan fallback encoding."""
    for encoding in ('utf-8', 'latin-1'):
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except Exception as e:
            raise ValueError(f"Error membaca file teks: {e}")
    raise ValueError("Tidak dapat membaca file teks: encoding tidak dikenali.")


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
    mime_lower = mime_type.lower()
    _, ext = os.path.splitext(file_path)
    ext_lower = ext.lower()

    if mime_lower == 'application/pdf' or ext_lower == '.pdf':
        return _extract_pdf(file_path)
    if 'wordprocessingml' in mime_lower or ext_lower == '.docx':
        return _extract_docx(file_path)
    if mime_lower in ('text/markdown', 'text/x-markdown') or mime_lower.startswith('text/plain') or ext_lower in ('.md', '.txt'):
        return _extract_text_file(file_path)

    raise ValueError(f"Format file tidak didukung: {mime_type} (extension: {ext})")


@contextmanager
def source_file_path(storage_path: str):
    """Yield a local path for local and remote Django storage backends."""
    try:
        yield default_storage.path(storage_path)
        return
    except NotImplementedError:
        pass

    _, extension = os.path.splitext(storage_path)
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=extension)
    temp_name = temp_file.name

    try:
        with temp_file, default_storage.open(storage_path, 'rb') as stored_file:
            for chunk in iter(lambda: stored_file.read(1024 * 1024), b''):
                temp_file.write(chunk)
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
            Source.objects.filter(id=source.id).update(extracted_text=raw_text)

        if not raw_text or not raw_text.strip():
            raise ValueError("File kosong atau tidak mengandung teks yang dapat diekstrak")

        normalized_text = normalize_text(raw_text)
        chunks = chunk_text(normalized_text, max_tokens=800, overlap=50)

        if not chunks:
            raise ValueError("Tidak ada chunks yang dihasilkan dari teks")

        embeddings = EmbeddingProvider.get_embeddings(chunks)
        chunk_objects = [
            SourceChunk(
                source=source,
                chunk_index=idx,
                text_content=chunk_text_content,
                token_count=count_tokens_approx(chunk_text_content),
                embedding=embeddings[idx],
                metadata={'status': 'ready'},
            )
            for idx, chunk_text_content in enumerate(chunks)
        ]
        SourceChunk.objects.bulk_create(chunk_objects)

        with transaction.atomic():
            source = Source.objects.select_for_update().get(id=source_id)
            source.status = 'ready'
            source.progress = 100
            source.error_message = ''
            source.save(update_fields=['status', 'progress', 'error_message', 'updated_at'])

    except Source.DoesNotExist:
        print(f"ERROR: Source dengan ID {source_id} tidak ditemukan")

    except Exception as e:
        error_traceback = traceback.format_exc()
        print(f"ERROR processing source {source_id}: {error_traceback}")

        if source is not None:
            with transaction.atomic():
                source = Source.objects.select_for_update().get(id=source.id)
                source.status = 'failed'
                source.error_message = str(e)[:500] if str(e) else 'Terjadi kesalahan saat memproses file.'
                source.save(update_fields=['status', 'error_message', 'updated_at'])
