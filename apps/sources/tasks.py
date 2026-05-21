"""Tasks untuk memproses source files."""

import os
import re
import traceback
from typing import List, Tuple

import fitz  # PyMuPDF
from django.conf import settings
from django.core.files.storage import default_storage

from apps.sources.models import Source, SourceChunk


class EmbeddingProvider:
    """Provider untuk menghasilkan embedding vector dari teks."""

    @staticmethod
    def get_embedding(text: str) -> List[float]:
        """Menghasilkan embedding vector dari teks."""
        # Placeholder implementation - generate dummy embedding
        # In production, replace with actual embedding API call (e.g., OpenAI, HuggingFace)
        # Using a simple hash-based approach for demonstration
        import hashlib

        # Generate a deterministic pseudo-embedding based on text hash
        # This creates a 768-dimensional vector (common embedding size)
        hash_obj = hashlib.sha256(text.encode('utf-8'))
        hash_bytes = hash_obj.digest()

        # Extend hash to create 768 dimensions (32 bytes * 24 = 768)
        embedding = []
        for i in range(768):
            byte_idx = i % len(hash_bytes)
            # Convert byte to float in range [-1, 1]
            value = (hash_bytes[byte_idx] / 127.5) - 1.0
            embedding.append(value)

        return embedding


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


def process_source(source_id: str) -> None:
    """Task RQ untuk memproses file source."""
    source = None
    try:
        # 1. Ambil objek Source berdasarkan ID
        source = Source.objects.get(id=source_id)

        # 2. Set status='processing', progress=0
        source.status = 'processing'
        source.progress = 0
        source.save(update_fields=['status', 'progress', 'updated_at'])

        # 3. Download file dari storage
        file_path = default_storage.path(source.storage_path)
        if not os.path.exists(file_path):
            # Try to access via storage's open method for remote storage
            try:
                with default_storage.open(source.storage_path, 'rb') as f:
                    # Read content to temporary location if needed
                    # For local storage, path() should work
                    pass
            except Exception as e:
                raise ValueError(f"File tidak ditemukan di storage: {source.storage_path}")

        # 4. Ekstrak teks dari file
        raw_text = extract_text_from_file(file_path, source.mime_type)

        if not raw_text or not raw_text.strip():
            raise ValueError("File kosong atau tidak mengandung teks yang dapat diekstrak")

        # 5. Normalisasi teks
        normalized_text = normalize_text(raw_text)

        # 6. Chunking teks
        chunks = chunk_text(normalized_text, max_tokens=500, overlap=50)

        if not chunks:
            raise ValueError("Tidak ada chunks yang dihasilkan dari teks")

        total_chunks = len(chunks)
        processed_chunks = 0

        # 7. Proses setiap chunk
        for idx, chunk_text_content in enumerate(chunks):
            # Buat objek SourceChunk dengan status='pending'
            chunk = SourceChunk(
                source=source,
                chunk_index=idx,
                text_content=chunk_text_content,
                token_count=count_tokens_approx(chunk_text_content),
                metadata={'status': 'pending'}
            )
            chunk.save()

            # Dapatkan embedding
            embedding = EmbeddingProvider.get_embedding(chunk_text_content)

            # Simpan embedding ke chunk, set status='ready'
            chunk.embedding = embedding
            chunk.metadata['status'] = 'ready'
            chunk.save(update_fields=['embedding', 'metadata'])

            # Update progress Source
            processed_chunks += 1
            progress_percentage = int((processed_chunks / total_chunks) * 100)
            source.progress = progress_percentage
            source.save(update_fields=['progress', 'updated_at'])

        # 8. Semua sukses, set status='ready'
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
            source.status = 'failed'
            source.error_message = error_traceback
            # Jangan reset progress, biarkan menunjukkan seberapa jauh proses berjalan
            source.save(update_fields=['status', 'error_message', 'updated_at'])

        # Jangan hapus file mentah - file tetap di storage


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