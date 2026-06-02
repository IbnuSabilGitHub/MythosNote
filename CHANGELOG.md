# Changelog

Semua perubahan penting di MythosNote dicatat di sini. Format mengikuti [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) dan versioning [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.51] - 2026-06-02
### Summary
Modularisasi dan refaktorisasi fitur "generate" (summary, mindmap, kuis, tabel) dengan memindahkannya dari `apps/sources` ke Django app terpisah `apps/generate`.

### Added
- `apps/generate/`: Standalone Django app baru untuk fitur AI generate.
- `config/settings.py`: Registrasi `apps.generate.apps.GenerateConfig` ke `INSTALLED_APPS`.
- `config/urls.py`: Routing `/` ke `apps.generate.urls`.

### Changed
- `apps/sources/models.py`: Penghapusan model `GenerateJob` (dipindah ke `apps/generate/models.py`).
- `apps/sources/tasks.py`: Penghapusan task `process_generate_job` (dipindah ke `apps/generate/tasks.py`).
- `apps/sources/urls.py`: Penghapusan routing `workspace-generate` (dipindah ke `apps/generate/urls.py`).
- `apps/sources/views.py`: Penghapusan `GenerateView` dan throttling terkait (dipindah ke `apps/generate/views.py`).

### Removed
- Model `GenerateJob`, task `process_generate_job`, dan `GenerateView` dari modul `sources`.

## [1.2.50] - 2026-05-29
### Summary
Implementasi AI Daily Quota + Security Mitigation untuk mencegah abuse (cost & storage exhaustion).

### Added
- `settings.py`:
  - `AI_DAILY_PROMPT_LIMIT` (default: 50)
  - `AI_DAILY_GENERATE_LIMIT` (default: 20)
  - `AI_DAILY_UPLOAD_LIMIT` (default: 10)
  - `WORKSPACE_MAX_SOURCES` (default: 15)

- `apps/accounts/models.py`: Tambah `upload_count` di model `UserUsage`
- `apps/accounts/utils.py`: Tambah `check_and_increment_upload()`

### Changed
- `apps/sources/views.py`:
  - `SourceUploadView.post`: Cek max sources (400) & daily upload quota (429)
  - `ChatView.post`: Cek daily prompt quota (429)
  - `GenerateView.post`: Cek daily generate quota (429)

### Notes
- Menggunakan atomic transaction (`select_for_update`) untuk cegah race condition
- Perlindungan ganda terhadap storage & cost exhaustion


## [1.2.49] - 2026-06-02
### Summary
Implementasi AI Daily Quota untuk membatasi penggunaan fitur generatif (chat & generate summary) per hari dan mencegah abuse/cost exhaustion.

### Added
- `settings.py`:
  - `AI_DAILY_PROMPT_LIMIT` (default: 50)
  - `AI_DAILY_GENERATE_LIMIT` (default: 20)

- `apps/accounts/utils.py`:
  - `get_api_usage()`
  - `check_and_increment_prompt()`
  - `check_and_increment_generate()`

### Changed
- `apps/sources/views.py`:
  - `ChatView.post()`: Cek kuota prompt → return 429 jika melebihi limit
  - `GenerateView.post()`: Cek kuota generate → return 429 jika melebihi limit

### Notes
- Menggunakan `select_for_update()` untuk mencegah race condition (atomic)
- Tetap mengaktifkan DRF throttling per-menit
- Keamanan tinggi terhadap concurrent requests


## [1.2.48] - 2026-06-02
### Summary
Pencegahan chat di luar topik dan validasi pilihan dokumen.

### Added
- **Auto-check Ready Sources**: Di `sources.js`, dokumen dengan status `ready` dicentang otomatis saat pertama kali dimuat.

### Changed
- `apps/sources/views.py`:
  - `ChatView.post` memvalidasi keberadaan `source_ids`. Menolak chat jika tidak ada dokumen yang terpilih.
  - Perbarui system prompt LLM agar hanya menjawab berdasarkan dokumen terpilih dan menolak pertanyaan luar topik.
- `static/js/workspace/selection.js`:
  - `getSelectedSourceIds` selalu mengembalikan daftar ID yang dipilih secara akurat (tidak lagi fallback ke kosong).
  - Mengirim event `sourceSelectionChanged` saat status pemilihan berubah.
  - Memperbaiki visual `#chat-source-counter` agar menampilkan `0/total` ketika tidak ada dokumen terpilih.
- `static/js/workspace/chat.js`:
  - Input teks chat dinonaktifkan jika tidak ada dokumen terpilih, dengan placeholder instruktif.

## [1.2.47] - 2026-06-02
### Summary
Implementasi Chat 3 (Quick Actions) pada panel sumber workspace.

### Added
- **Source Download**: Tombol download berkas cepat ditambahkan di sebelah tombol hapus pada item daftar sumber panel workspace.
- **SourceDownloadView**: Endpoint `GET /api/sources/<uuid:id>/download/` baru untuk mengunduh berkas dengan aman menggunakan `FileResponse` Django.

### Changed
- `apps/sources/urls.py`: Daftarkan routing baru untuk `source-download`.
- `static/js/workspace/sources.js`: Integrasikan tautan unduh dinamis dengan atribut download HTML5 dan penataan a11y focus.

## [1.2.46] - 2026-06-02
### Summary
Implementasi Chat 2 (Info Per File) dan Chat 4 (Safety + Polish) pada panel sumber workspace.

### Added
- **Selected info & Reset pilihan**: Ditambahkan panel informasi pilihan sumber (`1 sumber dipakai untuk chat`) dan tombol `Reset pilihan` di bawah "Semua File".

### Changed
- `apps/sources/serializers.py`: Menambahkan field `file_size`, `progress`, dan `error_message` ke `SourceListSerializer`.
- `apps/sources/views.py`: `SourceListView.get_queryset` memuat data `file_size`, `progress`, dan `error_message` secara efisien via `.only()`.
- `static/js/workspace/sources.js`:
  - Format tipe berkas (misal: `PDF`, `TXT`) di meta item berkas.
  - Penyesuaian string waktu dari `min lalu` ke `menit lalu`.
  - Penambahan progress bar mini di item sumber saat status `pending`/`processing`.
  - Penambahan visual pesan error berwarna merah di item sumber saat status `failed`.
  - Dialog konfirmasi browser interaktif saat klik tombol hapus berkas.
  - Penambahan focus style a11y pada check/button.
- `static/js/workspace/selection.js`: update status counter visual dan integrasi Reset button event listener.
- `templates/workspace.html`: penambahan markup `#selection-info-container`, penambahan styling keyboard focus ring, dan peningkatan accessibility (a11y) `aria-label`.

## [1.2.45] - 2026-06-01
### Summary
Polish dan perbaikan UI/UX pada workspace (3-panel layout & berbagai improvement).



### Polished
- 3-panel layout
- Token color primary
- Chat empty state
- Source cards yang lebih baik
- Chat input focus
- Mobile safe-area navigation
- Disabled state pada generate buttons
- Drag & upload state

## [1.2.44] - 2026-06-01
### Summary
Polish render markdown di chat agar lebih rapi dan nyaman dibaca.

### Changed
- `static/js/workspace/chat.js`: aktifkan opsi markdown `breaks` dan gunakan wrapper `chat-markdown`.
- `static/css/typography.css`: tambahkan styling markdown untuk heading, list, code block, quote, dan table.

## [1.2.43] - 2026-05-31
### Summary
Token efficiency Tahap 6: Dynamic Top-K RAG — jumlah chunks yang dikirim ke LLM disesuaikan dengan similarity score tertinggi.

### Changed
- `apps/sources/views.py`: `ChatView` — ganti `TOP_K = 5` (statis) dengan Dynamic Top-K:
  - `TOP_K_MAX = 8` — kandidat yang di-fetch dari pgvector
  - `TOP_K_MIN = 2` — chunk minimum jika sangat relevan
  - `SIM_HIGH = 0.85` → potong ke 2 chunk (query sangat spesifik)
  - `SIM_MED = 0.70` → potong ke 4 chunk (query relevan)
  - `< SIM_MED` → ambil semua 8 (query kurang spesifik)
  - Konversi `CosineDistance → similarity`: `similarity = 1.0 - distance`

### Notes
- Pertanyaan spesifik (similarity ≥ 0.85): kirim 2 chunk vs sebelumnya 5 — hemat 60% context token.
- Pertanyaan umum: kirim hingga 8 chunk untuk recall lebih baik vs sebelumnya 5.
- Threshold SIM_HIGH/SIM_MED bisa di-tune via class constants tanpa ubah logika.

## [1.2.42] - 2026-05-31

### Summary
Token efficiency Tahap 5 (terakhir): format context RAG dipersingkat, char limit dinaikkan.

### Changed
- `apps/sources/views.py`: `ChatView.post` — format label chunk diubah dari `"[Dokumen: filename]\n{content}"` menjadi `"[filename]: {content}"`. Hemat ~15 token per chunk × TOP_K chunks per request. `max_context_chars` dinaikkan `6000 → 8000` karena format lebih efisien.

## [1.2.41] - 2026-05-31

### Summary
Token efficiency Tahap 4: ringkas system prompt ChatView dari 5 baris menjadi 2 baris padat.

### Changed
- `apps/sources/views.py`: `ChatView.post` — system prompt dipersingkat; instruksi "jawab dari konteks" dan "no-hallucination" digabung menjadi 1 kalimat tanpa kehilangan semantik. Hemat ~50 token per request.

## [1.2.40] - 2026-05-31

### Summary
Token efficiency Tahap 3: naikkan chunk size 500 → 800 token untuk mengurangi jumlah chunks per dokumen.

### Changed
- `apps/sources/tasks.py`: `process_source` — ubah `chunk_text(..., max_tokens=500)` menjadi `max_tokens=800`. Menghasilkan lebih sedikit chunks per dokumen, mengurangi embedding API calls saat processing dan jumlah entri pgvector.

### Notes
- **Berlaku untuk dokumen baru saja.** Dokumen yang sudah diproses tidak di-reprocess otomatis; re-upload diperlukan untuk konsistensi.
- `overlap=50` tetap tidak berubah.

## [1.2.39] - 2026-06-01
### Summary
Security Vulnerability Hardening and remediation fixes.

### Security
- **Production Server**: Configured Docker and Docker Compose to run via Gunicorn instead of Django development server.
- **Rate Limiting**: Added DRF UserRateThrottle and AnonRateThrottle to protect Chat, Generate, and Source Upload endpoints.
- **Upload Validation**: Added magic-bytes signature verification (for PDF and DOCX) to block extension-spoofing bypasses.
- **Resource Cleanup**: Created Django `post_delete` signal for `Source` models to automatically purge physical files from disk/storage on deletion.
- **Internal Leakage**: Truncated generate job background task errors to 500 characters to prevent internal trace/path disclosure.
- **Security Headers**: Enabled `SECURE_REFERRER_POLICY` ('strict-origin-when-cross-origin') and `SECURE_CONTENT_TYPE_NOSNIFF` headers.
- **Supply Chain**: Pinned AI dependency versions (`google-genai==1.14.0`, `google-api-core==2.24.2`) in requirements.txt.
- **Input Validation**: Added 128-character limit for passwords and 254-character limit for emails across Django forms, HTML templates, and JS validation to prevent long-password DoS.
- **Upload Validation**: Added 150-character limit for uploaded filenames to prevent database insertion overflows and filesystem issues.

### Added
- **User Interface**: Designed and implemented a custom 404 error template with responsive UI and Iconify support.

### Fixed
- **Unit Tests**: Updated workspace name length validation tests to assert the configured 40-character limit.
- **Security Pentest**: Resolved split-index bug in CDN SRI test assertion.

### Removed
- **Dead Code**: Deleted `apps/chat` directory containing unused duplicate providers.

## [1.2.38] - 2026-06-01
### Summary
Security hardening and vulnerability fixes based on static code review.

### Security
- **Rate Limiting (XFF Spoofing)**: Limit trusted proxies configuration via `TRUSTED_PROXY_IPS` CIDR list to prevent spoofed XFF headers.
- **Upload Hardening**: Sanitize filenames with `get_valid_filename` and UUID prefixes to prevent path traversal and overwrite collisions.
- **Resource Limits (Parser/AI)**: Added file processing page caps (500 pages), text length limits (2M chars), RAG context limits (15k chars), and DeepSeek HTTP timeouts to prevent CPU and billing DoS.
- **Supply Chain**: Pinned CDN script versions and added SRI integrity hashes (`integrity=""` and `crossorigin=""`) in base and home templates.
- **Internal Leakage**: Removed exception string leaks from API responses and restricted the `django-rq` dashboard strictly to staff members via django URLs.

## [1.2.37] - 2026-05-31

### Summary
Remove OpenAI SDK and implementations; migrate fully to Gemini/DeepSeek.

### Changed
- `apps/sources/providers.py`: Remove `OpenAIEmbeddingProvider` and `OpenAIChatProvider`; default to `Gemini` for embeddings and keep `Gemini`/`DeepSeek` as supported chat providers.
- `requirements.txt`: Remove `openai` dependency.
- `apps/sources/tests.py`: Remove/adjust tests referencing OpenAI provider.

### Notes
- This change removes OpenAI-specific code paths and dependencies. Use `AI_PROVIDER=gemini` or `AI_PROVIDER=deepseek` with respective API keys.

## [1.2.36] - 2026-05-30
### Summary
Implementasi Tahap 6: Source Selection — filter RAG berdasarkan source yang dipilih.

### Added
- `static/js/workspace/selection.js`: Rewrite untuk support dynamic re-bind items, expose `getSelectedSourceIds()`, update counter badge `#chat-source-counter`.

### Changed
- `apps/sources/views.py`: `ChatView.post` terima parameter `source_ids` (list UUID), filter chunk RAG berdasarkan source terpilih; fallback ke semua ready source jika kosong.
- `static/js/workspace/chat.js`: Kirim `source_ids` dari `WorkspaceSelection` ke API chat.
- `templates/workspace.html`: Tambah `id="chat-source-counter"` di header chat untuk menampilkan jumlah/pilihan sumber.

## [1.2.35] - 2026-05-30
### Summary
Implementasi Tahap 5: Frontend Chat yang dinamis dan terhubung dengan backend RAG.

### Added
- `static/js/workspace/chat.js`: Skrip frontend baru untuk mengelola state chat, merender pesan dinamis (user & AI), loading indicator, dan integrasi API.

### Changed
- `templates/workspace.html`: Ubah UI statis panel chat menjadi kontainer dinamis, tambah form interaktif.

## [1.2.34] - 2026-05-30
### Summary
Implementasi Tahap 4: RAG Normal dengan context limit, Indonesian system prompt, dan filter/sources response metadata.

### Added
- `apps/sources/views.py`: Tambah `ChatMessageDeleteView` untuk hapus seluruh riwayat chat di workspace

### Changed
- `apps/sources/views.py`: Update RAG pipeline di `ChatView` (top 5 CosineDistance, max context limit 6000 karakter, Indonesian system prompt, dan list sources di response)
- `apps/sources/urls.py`: Daftarkan endpoint DELETE messages

## [1.2.33] - 2026-05-30
## [1.2.32] - 2026-05-30
### Summary
Persistensi chat AI per workspace sudah ditambahkan.

### Added
- `apps/sources/models.py`: Tambah model `ChatSession` untuk simpan percakapan per workspace
- `apps/sources/models.py`: Tambah model `ChatMessage` untuk simpan pesan user dan assistant
- `apps/sources/migrations/0003_chatsession_chatmessage.py`: Migrasi skema baru untuk chat persistence

### Notes
- Chat sekarang punya struktur data yang jelas untuk sesi dan pesan
- Siap dipakai untuk history, sinkronisasi, dan pengembangan fitur chat berikutnya

## [1.2.31] - 2026-05-29
### Summary
Perbaikan Gemini Embedding Provider: ganti SDK dan model embedding yang benar.

### Fixed
- Ganti SDK dari `google.generativeai` ke `google-genai`
- Ubah model dari `text-embedding-004` ke `gemini-embedding-001` (dimensi 768)
- Perbaikan endpoint embedContent yang tidak support model lama

### Changed
- `providers.py`: Update `GeminiEmbeddingProvider`
- `settings.py`, `.env`, `.env.example`: Update konfigurasi model
- `README.md` & `tests`: Penyesuaian dokumentasi dan test

### Notes
- Model yang benar sekarang `gemini-embedding-001`
- Dimensi embedding = 768

## [1.2.30] - 2026-05-29
### Summary
Penghapusan OpenAI Embedding Provider dan migrasi default ke Gemini.

### Changed
- `embeddings.py`: Hapus `OpenAIEmbeddingProvider` beserta importnya
- `.env.example`: Hapus `OPENAI_API_KEY`
- `settings.py`:
  - Hapus load `OPENAI_API_KEY`
  - Tambah `DEFAULT_EMBEDDING_PROVIDER = 'gemini'`
  - Ubah mekanisme pengambilan `EMBEDDING_PROVIDER`
  - Tambah `EMBEDDING_MODEL = 'models/embedding-001'`
- `PROJECT_CONTEXT.md`: Tambah section **Migration to Gemini/DeepSeek**
- `README.md`: Update prerequisite jadi **Gemini API Key** (free tier supported)

### Notes
- Default embedding provider sekarang Gemini
- OpenAI dependency berhasil dihapus

## [1.2.29] - 2026-05-29
### Summary
Implementasi RAG flow di `ChatView.post` menggunakan cosine similarity via pgvector.

### Changed
- `views.py`:
  - Import `CosineDistance` dan `EmbeddingProvider`
  - Tambah RAG retrieval: embedding query → filter & order `SourceChunk` (top 5)
  - Fallback message jika tidak ada chunk relevan
  - Gabungkan context ke `ChatProvider.chat_complete()`

### Notes
- Response format tetap sama (`{"response": "..."}`)
- Sudah kompatibel dengan semua embedding provider

## [1.2.28] - 2026-05-29
### Summary
Implementasi `GeminiEmbeddingProvider` dengan retry logic (exponential backoff) untuk meningkatkan kestabilan koneksi ke Google Gemini Embedding API.

### Changed
- `providers.py`: Penambahan implementasi lengkap `GeminiEmbeddingProvider` yang mewarisi `BaseEmbeddingProvider`


## [1.4.27] - 2026-05-29
### Summary
Refactoring modul embeddings untuk menambahkan `LocalEmbeddingProvider` sebagai placeholder dan meningkatkan kompatibilitas dengan pgvector, sambil menjaga backward compatibility penuh.

### Added
- Class `LocalEmbeddingProvider` di `embeddings.py` (placeholder dengan `NotImplementedError`)
- Export `LocalEmbeddingProvider` beserta 6 provider existing di `embeddings.py`
- Support opsi `"local"` pada fungsi `_create_embedding_provider()`

### Changed
- `embeddings.py`:
  - Menambahkan docstring utama: "All providers return vectors compatible with pgvector storage"
- `providers.py`:
  - `BaseEmbeddingProvider`: Menambahkan docstring tentang dimensi vector yang compatible dengan pgvector
  - `_create_embedding_provider()`: Menambahkan penanganan provider "local"

### Notes
- Method signature `get_embedding(text: str) -> list[float]` tetap unchanged
- Worker call pattern dan kompatibilitas existing tetap terjaga
- Tidak ada referensi OpenAI di abstract base class (persiapan penghapusan OpenAI dependency di masa depan)

## [1.4.26] - 2026-05-29

### Summary
Migrasi kembali penyimpanan file ke Django FileSystemStorage (default_storage) dengan volume bersama (shared volume) Docker Compose.

### Fixed
- **Docker Compose** (`docker-compose.yml`):
  - Menambahkan volume bersama `media_data` ke service `web` dan `worker` untuk sinkronisasi berkas media.
- **Django Storage** (`apps/sources/views.py`, `apps/sources/tasks.py`):
  - Mengembalikan alur penyimpanan file dari Supabase Storage ke `default_storage` Django (FileSystemStorage) yang menyimpan berkas di bawah `MEDIA_ROOT`.
  - Memperbarui views upload/delete dan task RQ untuk membaca berkas dari media bersama.

## [1.4.25] - 2026-05-29

### Summary
DOCX support dan polish UX fitur upload sumber.

### Added
- **DOCX support** (`requirements.txt`, `views.py`, `tasks.py`):
  - `python-docx==1.1.2` ditambahkan ke dependencies
  - `.docx` ditambahkan ke `ALLOWED_EXTENSIONS` di `views.py`
  - Handler DOCX di `extract_text_from_file()` menggunakan `python-docx`
  - `tabler:file-type-docx` icon di `sources.js`

### Changed
- `apps/sources/views.py`:
  - Error messages diubah ke Bahasa Indonesia yang user-friendly:
    - `"Format tidak didukung. Gunakan PDF, TXT, MD, atau DOCX."`
    - `"File terlalu besar. Maksimal 20 MB."`
    - `"File dengan nama ini sudah ada di workspace."`
- `apps/sources/tasks.py`:
  - `error_message` yang tersimpan di DB dibatasi 500 karakter (bukan full traceback)
  - Traceback lengkap tetap dicetak ke log
- `static/js/workspace/index.js`:
  - Upload via XHR (menggantikan `fetch`) untuk mendukung progress event
  - Progress bar terintegrasi di modal (`upload-progress-wrap`, `upload-progress-bar`)
  - Drag-and-drop file ke drop zone
  - DOCX ditambahkan ke `ALLOWED_EXT`
  - Error response dari API di-map ke pesan user-friendly
- `static/js/workspace/sources.js`:
  - `fileIconMap` mendukung `docx` → `tabler:file-type-docx`
  - Status badge `pending`/`processing` menampilkan `animate-pulse`
  - Label status diubah ke Bahasa Indonesia: Menunggu / Memproses / Siap / Gagal
  - Badge `failed` menampilkan `title` dengan pesan error pendek (hover)
  - `queued` status ditangani sebagai alias `pending`
- `templates/workspace.html`:
  - File input `accept` diperbarui ke `.pdf,.txt,.md,.docx`
  - Teks hint drop zone diperbarui
  - Progress bar HTML ditambahkan ke modal

## [1.4.24] - 2026-05-29


### Summary
Menghubungkan Sources Panel di `workspace.html` ke backend API upload, list, delete, dan status polling.

### Added
- Upload modal di `workspace.html`: overlay backdrop, drop zone file, preview nama/ukuran file, validasi ekstensi dan ukuran, tombol cancel/upload
- `id="workspace-data"` bridge div yang membawa `{{ active_workspace.id }}` ke JavaScript
- `id="source-list-container"` pada div daftar sumber agar `WorkspaceSources` bisa me-render dinamis
- `id="btn-add-source"` pada tombol "Tambah Sumber" untuk event binding

### Changed
- `workspace.html`:
  - Hardcoded source items dihapus; JS yang me-render daftar
  - "Tambah Sumber" `<div>` diubah menjadi `<button>` dengan `id="btn-add-source"`
  - Upload modal HTML ditambahkan sebelum `{% endblock %}`
- `static/js/workspace/index.js` — Ditulis ulang sepenuhnya:
  - Inisialisasi `WorkspaceSources` dari `data-workspace-id`
  - Logic open/close/reset modal
  - Validasi file (ekstensi `.pdf/.txt/.md`, maks 20 MB)
  - Preview file (icon berdasarkan ekstensi, nama, ukuran)
  - Submit form → `workspaceSources.uploadSource(formData)` → tutup modal + toast
- `static/js/workspace/sources.js`:
  - Tambah `getCSRFToken()` helper (baca dari cookie `csrftoken`)
  - `X-CSRFToken` header ditambahkan ke `uploadSource()` dan `deleteSource()`
  - `createSourceItemHTML()` diperbarui agar cocok dengan desain `workspace.html`:
    - Checkbox (warna berbeda saat ready vs pending)
    - Icon file berdasarkan ekstensi (`tabler:pdf`, `tabler:txt`, `tabler:markdown`)
    - Nama file dengan font Manrope
    - Metadata: waktu relatif + ukuran file
    - Status badge minimalis (10px)
    - Tombol hapus lebih kecil di sisi kanan

### Notes
- `config/views.py` sudah melewatkan `active_workspace` ke template — tidak ada perubahan
- `WorkspaceSources.fetchSources()` dipanggil otomatis saat halaman dimuat
- `WorkspaceSources.pollSourceStatus()` dimulai otomatis setelah upload berhasil

## [1.4.23] - 2026-05-27


### Summary
Penambahan field `extracted_text` pada model Source dan konfigurasi media file handling.

### Added
- Field `extracted_text` di model `Source` untuk menyimpan hasil ekstraksi teks dari dokumen
- Konfigurasi `MEDIA_ROOT` dan `MEDIA_URL` di settings
- Serving media files saat `DEBUG=True`

### Changed
- `config/settings.py`:
  - Menambahkan `MEDIA_ROOT` dan `MEDIA_URL`
  - Menambahkan `SessionAuthentication` di `REST_FRAMEWORK`
  - Menghapus entry `'sources'` yang sudah tidak digunakan

- `apps/sources/models.py`:
  - Tambah `extracted_text = TextField(blank=True, default='')` pada model `Source`

- `apps/sources/tasks.py`:
  - Update `extracted_text` setelah proses ekstraksi teks selesai

- `config/urls.py`:
  - Menambahkan static media serving untuk mode development (`DEBUG=True`)

- Migration `0002_source_extracted_text.py` telah digenerate

### Notes
- `.gitignore` sudah benar memiliki `/media/` (tidak perlu perubahan)
- Persiapan untuk fitur RAG dan preview dokumen di masa depan

## [1.4.22] - 2026-05-27

### Summary
Migrasi storage dari Google Cloud Storage (GCS) ke **Supabase Storage**.

### Changed
- **Dependency**:
  - `requirements.txt`: Mengganti `google-cloud-storage` menjadi library `supabase`

- **Environment & Settings**:
  - `.env`: Hapus kredensial GCS, tambah `SUPABASE_URL`, `SUPABASE_KEY`, dan `SUPABASE_BUCKET`
  - `.env.example`: Diperbarui sesuai perubahan
  - `config/settings.py`: Menambahkan pembacaan variabel Supabase

- **Sources Storage Utils**:
  - `apps/sources/utils.py`: File baru untuk handle upload/download menggunakan Supabase SDK
  - Implementasi `client.storage.from_(bucket).upload()`

- **Integrasi**:
  - `views.py`: Update fungsi upload & delete
  - `tasks.py`: Update download untuk processing

- **Dokumentasi**:
  - `Architecture.md`: Semua referensi GCS diganti ke Supabase Storage
  - `PROJECT_CONTEXT.md`: Update deskripsi library, environment, dan arsitektur storage

## [1.4.21] - 2026-05-26

### Summary
Perbaikan konfigurasi Docker dan database untuk mendukung pgvector dengan lebih stabil.

### Fixed
- `docker-compose.yml`: Menggunakan image resmi `pgvector/pgvector:pg16`
- `apps/sources/migrations/0001_initial.py`: Mengaktifkan `VectorExtension` secara benar
- `Dockerfile`: 
  - Menggunakan `package-lock.json` + `npm ci` untuk instalasi dependencies frontend yang lebih konsisten
  - Menghapus comment yang rusak pada bagian ENV

### Improvements
- Docker setup untuk PostgreSQL dengan pgvector menjadi lebih reliable
- Proses build frontend lebih stabil dan reproducible
- Migration vector extension berjalan sesuai best practice

## [1.4.20] - 2026-05-25

### Summary
Penambahan limit panjang nama workspace menjadi maksimal 40 karakter pada fitur Create dan Rename.

### Added
- Validasi panjang nama workspace (max 40 karakter) di backend dan frontend
- Test baru untuk validasi nama workspace

### Changed
- **Backend Validation**:
  - `apps/workspaces/utils.py`
  - `config/views.py` (atau workspace views)

- **Frontend Validation**:
  - `project.js`
  - `templates/components/workspace_create_modal.html`
  - `templates/components/workspace_rename_modal.html`

### Improvements
- User tidak dapat membuat atau mengubah nama workspace melebihi 40 karakter
- Validasi dilakukan baik di sisi server maupun client-side (lebih responsif)
- Pesan error yang jelas jika melebihi batas
- Unit test ditambahkan untuk memastikan validasi berjalan dengan baik

## [1.4.19] - 2026-05-24

### Summary
Mitigasi race condition pada sistem Workspace Quota — Membuat proses create workspace menjadi atomic dan thread-safe.

### Fixed
- Race condition pada pengecekan quota workspace per user

### Changed
- Create workspace dipindahkan ke **service atomik**
- Menggunakan `select_for_update()` untuk lock row user saat pengecekan quota
- Quota direcheck ulang di dalam transaksi database
- Jika quota sudah penuh, mengembalikan status **409 Conflict**
- Operasi create, rename, dan delete workspace sekarang dikenakan **rate limiting** (return **429 Too Many Requests**)

### Technical Improvements
- Proses create workspace menjadi fully atomic
- Mencegah user membuat lebih dari 10 workspace meskipun dilakukan secara bersamaan (race condition)
- Branch: `fix/workspace-quota-race`

### Notes
- Keamanan quota workspace jauh lebih baik
- User experience tetap terjaga dengan response yang jelas (409 & 429)
- Perlindungan terhadap concurrent request dan potensi abuse

## [1.4.18] - 2026-05-24

### Summary
Implementasi batas maksimal workspace (Quota Limit) per user — maksimal 10 workspace.

### Added
- Sistem Workspace Quota di server-side
- Validasi dan penolakan create workspace jika limit tercapai
- Tampilan sisa slot workspace di UI

### Changed
- **Server Side** (`apps/workspaces/utils.py` & `config/views.py`):
  - Aturan quota maksimal 10 workspace per user
  - Project view menolak create workspace baru jika limit tercapai
  - Mengirim toast warning via Django messages

- **Frontend / UI**:
  - `templates/project.html`: Tombol create, kartu create, dan indikator kuota otomatis disable saat limit tercapai
  - `templates/components/workspace_create_modal.html`: Modal create workspace juga terkunci jika kuota habis
  - Menampilkan informasi **sisa slot workspace** yang tersedia

### Notes
- Batas quota diputuskan dan divalidasi di **server-side** (aman dari bypass)
- User mendapat feedback yang jelas baik melalui toast maupun disabled UI
- Pengalaman pengguna lebih terarah dan mencegah penyalahgunaan

## [1.4.17] - 2026-05-24

### Summary
Peningkatan UX pada Workspace Dashboard — Delete menggunakan modal custom dan implementasi Toast Notification.

### Changed
- Delete workspace sekarang menggunakan **modal custom** (bukan `confirm()` browser)
- Toast notification diaktifkan untuk operasi **Create**, **Rename**, dan **Delete** workspace
- Rename workspace memperbarui kartu secara dinamis tanpa reload halaman

### Files Changed
- `base.html`: Load script toast dengan benar (line 149) agar flash message muncul setelah redirect
- `project.html`: Tombol delete membawa nama workspace dan include modal delete baru (line 69)
- `workspace_delete_modal.html`: Modal delete dengan UI destructive yang lebih baik
- `project.js`: Logic rename & delete menggunakan toast sukses/gagal

### Improvements
- Pengalaman pengguna lebih modern dan konsisten
- Delete action lebih aman dengan konfirmasi modal custom
- Feedback sukses/gagal langsung ditampilkan via toast
- Rename workspace terasa lebih responsif (tanpa reload)


## [1.4.16] - 2026-05-23

### Summary
Transformasi halaman Project menjadi **Workspace Dashboard** dengan fitur manajemen workspace lengkap (Create, Rename, Delete).

### Added
- Workspace API endpoints untuk rename dan delete workspace (`views.py` & `urls.py`)
- Frontend logic baru di `project.js` untuk handle aksi rename & delete workspace
- Modal UI baru:
  - `workspace_create_modal.html`
  - `workspace_rename_modal.html`
- Migration baru untuk mendukung model Workspace

### Changed
- Routing: Menambahkan halaman workspace baru di `urls.py`
- `views.py` (Project View):
  - Bisa membuat workspace baru
  - Redirect otomatis setelah create
  - Mengambil daftar workspace beserta `source_count`
- `project.html` (Template):
  - Diubah menjadi **Workspace Dashboard**
  - Menampilkan kartu workspace dengan informasi nama, tanggal dibuat, dan jumlah source
  - Tombol Create Workspace
  - Menu Rename & Delete per workspace
  - Include modal create & rename
  - Load JavaScript `project.js` baru

### Notes
- Halaman Project sekarang berfungsi sebagai pusat manajemen workspace
- User experience jauh lebih baik dengan antarmuka yang lebih kaya dan interaktif
- Data workspace ditampilkan lebih informatif (termasuk jumlah source di dalamnya)

#### [1.4.15] - 2026-05-22
##### Summary
Implementasi API endpoint untuk fitur Chat (berbasis *Retrieval-Augmented Generation*/RAG) dan fungsi Generate secara asinkron (*background jobs*), beserta model dan worker task terkait [1, 2].

##### Added
*  **API Endpoints** (`views.py` & `urls.py`):
    *  **Chat API** (`POST /api/workspace/<id>/chat/`): Endpoint untuk percakapan AI. Menerima pesan pengguna, membangun konteks secara dinamis dari *source chunks* yang berstatus `ready`, memanggil `ChatProvider.chat_complete`, dan mengembalikan respons [3].
    *  **Generate API** (`POST /api/workspace/<id>/generate/`): Endpoint untuk memicu aksi *quick generate* (seperti ringkasan, tabel, kuis, atau mindmap). Melakukan validasi *action*, membuat objek `GenerateJob` dengan status `queued`, memasukkannya ke antrean RQ (enqueue), dan langsung mengembalikan respons berisi `id` dan `status` dari job tersebut [2, 3].
*  **Model Database** (`models.py`):
    *  Menambahkan model *job* (seperti `GenerateJob`) untuk melacak status eksekusi tugas asinkron (misalnya: *queued*, *processing*, *success*, *failed*) [3].
*  **Async Background Tasks** (`tasks.py`):
    *  Implementasi fungsi `process_generate_job(job_id, prompt)` sebagai antrean pekerja (worker) dengan alur kerja berikut:
        *  Mengubah status `GenerateJob` menjadi `processing`.
        *  Memanggil `ChatProvider.chat_complete` dengan *prompt* yang telah disiapkan.
        *  Memperbarui status job menjadi `success` beserta hasil akhirnya, atau menjadi `failed` beserta `error_message` jika terjadi kegagalan [2].

##### Files Affected
**Modified/Added:**
*  `views.py` *(modul terkait workspace/chat)*
*  `urls.py` *(penambahan routing endpoint baru)*
*  `models.py` *(penambahan job model)*
*  `tasks.py` *(implementasi async processing untuk generate)*

##### Notes
*  Proses chat dengan konteks dokumen berjalan secara sinkron/langsung memanggil provider, 

## [1.4.14] - 2026-05-22

### Changed
- Refactor: Pisahkan berkas JavaScript di `static/js/` berdasarkan tanggung jawab (Separation of Concerns). Perubahan utama:
  - Pindah `static/js/auth-validation.js` → `static/js/auth/validation.js`
  - Pindah `static/js/components.js` → `static/js/ui/loading-button.js`
  - Pindah `static/js/toast.js` → `static/js/toast/manager.js`
  - Pindah `static/js/messages.js` → `static/js/toast/django-messages.js`
  - Memecah `static/js/workspace.js` menjadi modul: `static/js/workspace/sources.js`, `static/js/workspace/layout.js`, `static/js/workspace/selection.js`, `static/js/workspace/index.js`
  - Memperbarui template untuk memuat jalur skrip baru dan menghapus pemanggilan berkas lama.


#### [1.4.13] - 2026-05-22
##### Summary
Implementasi *frontend* `WorkspaceUI` untuk mendukung interaksi manajemen dokumen (*source*) secara *real-time* di antarmuka pengguna.

##### Added
*  **Frontend Class** (`workspace.js`):
    *  Membuat *class* terpadu `WorkspaceUI` yang akan diinisialisasi otomatis saat halaman dimuat (sebagai global instance `workspaceUI`).
    *  Membaca `workspaceId` secara otomatis dari atribut `data-workspace-id` pada DOM atau melalui parameter URL.
*  **Metode Utama (`WorkspaceUI`)**:
    *  `fetchSources()`: Mengambil daftar *source* (GET) dan meneruskannya ke fungsi render.
    *  `renderSourceList()`: Membuat elemen daftar dokumen yang dilengkapi dengan badge status dan tombol hapus.
    *  `uploadSource(formData)`: Mengirim file via POST, memperbarui daftar, dan langsung memicu proses *polling* status.
    *  `pollSourceStatus(sourceId)`: Melakukan *polling* status setiap 2 detik hingga dokumen berstatus `ready` atau `failed`. Mencegah duplikasi *polling* menggunakan struktur data `Map`.
    *  `deleteSource(sourceId)`: Mengirim permintaan DELETE dengan UX animasi penghapusan yang mulus (*smooth removal*), disertai fitur *rollback* (mengembalikan elemen) jika permintaan gagal.
*  **Fitur & Penanganan State (UI/UX)**:
    *  **States**: Penanganan state dinamis mencakup *Loading* (dengan animasi *spinner*), *Empty* (pesan "No sources uploaded"), dan *Error* (tombol *retry* beserta notifikasi *toast*).
    *  **Styling**: Kelas CSS dinamis berdasarkan status (`.status-pending`, `.status-ready`, `.status-failed`).
    *  **Keamanan**: Implementasi *HTML escaping* secara internal untuk menghindari kerentanan XSS pada render data pengguna.

##### Files Affected
**Added/Modified:**
*  `static/js/workspace.js` *(atau path javascript terkait)*

#### [1.4.12] - 2026-05-22
##### Summary
Penyempurnaan API `sources` untuk list, upload, delete, dan status pemrosesan.

##### Changed
*  `apps/sources/views.py`: Alur upload, list, status, dan delete dirapikan; validasi upload dibuat lebih ketat dan antrian task ditangani lebih aman.
*  `apps/sources/serializers.py`: Serializer dibuat lebih ringkas untuk respons daftar dan detail source.
*  `apps/sources/tasks.py`: Proses pemrosesan source diperkuat agar lebih aman untuk storage lokal maupun remote.
*  `apps/sources/urls.py`: Routing disesuaikan dengan struktur endpoint baru.

#### [1.4.11] - 2026-05-21
##### Summary
Implementasi API endpoint untuk membaca daftar, detail, dan status `Source` (dokumen) beserta fungsionalitas penghapusan file.

##### Added
*  **Views API Manajemen Source** (`apps/sources/views.py`):
    *  `SourceListView`: Endpoint untuk menampilkan daftar *source* milik pengguna (*user-filtered*). Mendukung paginasi (10 item per halaman) dan filter tambahan berdasarkan `workspace_id` dan `status`.
    *  `SourceDetailView`: Endpoint untuk mengambil informasi detail (`GET`) dan menghapus (`DELETE`) *source*. Aksi `DELETE` secara otomatis akan menghapus file *raw* mentah dari sistem *storage*.
    *  `SourceStatusView`: Endpoint spesifik untuk mengecek status pemrosesan dokumen.
*  **Serializers** (`apps/sources/serializers.py`):
    *  Menambahkan serializer dengan format ringkas (summary).
    *  Menambahkan serializer khusus untuk memuat status dokumen.
*  **Routing URL**:
    *  Menambahkan URL *routes* baru untuk view di atas pada `apps/sources/urls.py`.

##### Changed
*  Memperbarui `urls.py` utama proyek untuk me-*mount* URL aplikasi `sources`.

##### Files Affected
**Modified:**
*  `apps/sources/views.py`
*  `apps/sources/serializers.py`
*  `apps/sources/urls.py`
*  `config/urls.py` *(atau file root urls tempat mount dilakukan)*

#### [1.4.10] - 2026-05-21
##### Summary
Penambahan dukungan `DeepSeek` sebagai opsi Chat/Completion provider (kompatibel dengan SDK OpenAI via `base_url`).

##### Added
*  **Chat Provider** (`apps/sources/providers.py`):
  - `DeepSeekChatProvider`: Chat/completion provider yang membungkus SDK `openai.OpenAI` dengan `base_url` yang dapat dikonfigurasi untuk endpoint DeepSeek.
*  **Environment variables**: `DEEPSEEK_API_KEY` dan `DEEPSEEK_BASE_URL` ditambahkan ke `.env.example` dan `config/settings.py`.
*  **Tests**: Penambahan test untuk pemilihan provider `deepseek` dan validasi `DEEPSEEK_API_KEY`.

##### Changed
*  `config/settings.py`: Menambahkan pembacaan `DEEPSEEK_API_KEY` dan `DEEPSEEK_BASE_URL`, serta validasi `AI_PROVIDER` untuk menerima `deepseek`.
*  `README.md` & `Architecture.md`: Dokumentasi konfigurasi DeepSeek ditambahkan.

##### Files Affected
**Added / Modified:**
*  `apps/sources/providers.py`
*  `config/settings.py`
*  `.env.example` / `.env`
*  `README.md`
*  `apps/sources/tests.py`


#### [1.4.9] - 2026-05-21
##### Summary
Implementasi sistem Embedding Provider (OpenAI & Gemini) untuk menggantikan placeholder dan mendukung integrasi pembuatan vektor dokumen.

##### Added
*  **Modul Embeddings** (`apps/sources/embeddings.py`):
    *  `BaseEmbeddingProvider`: Abstract Base Class (ABC) yang mendefinisikan interface standar `get_embedding(text) -> list[float]`.
    *  `OpenAIEmbeddingProvider`: Implementasi provider menggunakan model `text-embedding-3-small` (membutuhkan `OPENAI_API_KEY`).
    *  `GeminiEmbeddingProvider`: Implementasi provider menggunakan model `models/embedding-001` (membutuhkan `GEMINI_API_KEY`).
    *  `EmbeddingProvider`: *Lazy default instance* yang memuat provider secara dinamis berdasarkan konfigurasi `EMBEDDING_PROVIDER` (pilihan: `openai` atau `gemini`, default: `openai`).
*  Variabel environment pendukung ditambahkan ke `.env.example` (`EMBEDDING_PROVIDER=openai`).

##### Changed
*  `config/settings.py`: Menambahkan pemuatan konfigurasi `OPENAI_API_KEY`, `GEMINI_API_KEY`, dan `EMBEDDING_PROVIDER` dari environment variables.
*  `apps/sources/tasks.py`: Menghapus fungsi generator embedding *placeholder* lama dan menggantinya dengan import `EmbeddingProvider` langsung dari modul `embeddings`.
*  `requirements.txt`: Menambahkan pustaka resmi `openai` dan `google-generativeai` ke dalam daftar dependensi proyek.

##### Files Affected
**Added:**
*  `apps/sources/embeddings.py`

**Modified:**
*  `config/settings.py`
*  `apps/sources/tasks.py`
*  `requirements.txt`
*  `.env.example`

#### [1.4.8] - 2026-05-21
##### Summary
Implementasi background worker untuk ekstraksi teks, chunking, dan embedding dokumen menggunakan RQ task (Branch: `feat/sources-worker-chunking`).

##### Added
-  **Fungsi Utama**: `process_source(source_id)` diimplementasikan sebagai RQ task dengan alur kerja berikut:
    -  Mengambil objek `Source` berdasarkan ID.
    -  Update state dokumen secara real-time (set `status='processing'`, `progress=0`, dan update persentase seiring berjalannya chunking).
    -  Mengunduh file dari storage menggunakan `default_storage`.
    -  Ekstraksi teks spesifik format: menggunakan PyMuPDF (fitz) untuk PDF, dan pembacaan teks langsung untuk .md dan .txt.
    -  Membuat objek `SourceChunk` (awal `status='pending'`, kemudian `ready`) yang memuat hasil chunking teks dan vektor embedding.
    -  Menyimpan traceback string ke `error_message` dan menetapkan `status='failed'` jika terjadi kegagalan sistem.
    -  Menambahkan blok guard `if __name__ == '__main__':` dengan `django.setup()` agar task bisa dites secara standalone.
-  **Helper Functions**: 
    -  `EmbeddingProvider.get_embedding()`: Menghasilkan 768-dimensi embedding (saat ini menggunakan *placeholder* berbasis hash).
    -  `normalize_text()`: Berfungsi untuk menormalisasi teks dengan menghapus whitespace ganda.
    -  `count_tokens_approx()`: Melakukan estimasi jumlah token secara kasar (panjang karakter / 4).
    -  `chunk_text(text, max_tokens=500, overlap=50)`: Algoritma pemecah teks hierarkis berdasarkan paragraf → kalimat → kata.
    -  `extract_text_from_file()`: Melakukan ekstraksi teks dengan validasi berbasis MIME type.

##### Files Changed
-  `/workspace/apps/sources/tasks.py`

##### Notes
-  Sistem sengaja **tidak menghapus** file mentah dari storage setelah proses ekstraksi selesai.
-  Format file yang tidak dikenali atau aneh akan dicatat melalui penanganan error (error logging).
-  Penghitungan token (tokenization) masih berupa estimasi kasar dan generator embedding masih menggunakan placeholder yang nantinya perlu diganti dengan API/Model Embedding yang sesungguhnya.

## [1.4.7] - 2026-06-21

### Added
- **Source Upload API**: Endpoint `POST /api/sources/upload/` untuk upload file source ke workspace.
  - Validasi: workspace ownership, ekstensi file (.pdf/.md/.txt), maks 20MB, penolakan duplikat nama file.
  - File disimpan ke Django storage, objek Source dibuat dengan status `pending`.
  - Enqueue job RQ (`apps.sources.tasks.process_source`) untuk pemrosesan async.
  - Serializer Source, task RQ placeholder, app configs untuk sources/workspaces.

## [1.4.6] - 2026-05-20

### Summary
Refactor struktur direktori project — Memindahkan app `accounts` ke dalam folder `apps/`.

### Changed
- **Directory Structure Refactor**:
  - Memindahkan seluruh aplikasi `accounts` dari root project ke `apps/accounts/`
  - Menghapus folder `accounts/` lama (semua file di-move)
  - Memperbarui semua import dan referensi ke app accounts

### Files Affected
**Modified:**
- `config/settings.py` (update `INSTALLED_APPS`, import paths, dll)
- `config/urls.py`
- `config/views.py`

**Moved:**
- `accounts/` → `apps/accounts/`

### Notes
- Semua import lama sudah diperbarui
- Struktur project sekarang lebih rapi dan scalable (mengikuti best practice Django untuk multiple apps)
- Siap menampung app baru di dalam folder `apps/` (contoh: `sources`, `workspaces`, dll)

## [1.4.5] - 2026-05-20
### Summary
Implementasi model utama `Source` dan `SourceChunk` untuk sistem manajemen dokumen dan RAG.

### Added
- `apps/sources/models.py`:
  - Model **Source**: Menyimpan informasi file sumber (dokumen) yang diupload user
  - Model **SourceChunk**: Menyimpan potongan-potongan teks (chunk) beserta embedding vector

## [1.4.4] - 2026-05-14

### Summary
Implementasi perbaikan keamanan Authentication Flow (Anti-Enumeration & Rate Limiting).

### Fixed / Improved
- Signup enumeration protection: response signup dibuat generic
- Resend verification button disembunyikan setelah signup (mencegah user enumeration)
- Login timing padding untuk mengurangi timing attack
- Rate limiting counters dibuat lebih atomic
- Login lockout per IP address
- Failed login counter di-lock setelah batas tertentu
- Production cookies di-hardening (security improvement)
- Penambahan unique constraint pada field email (migration 0004)

### Files Changed
- `accounts/forms.py`
- `accounts/views.py`
- `accounts/backends.py`
- `accounts/utils.py`
- `templates/auth/email_unverified.html`
- `config/settings.py`
- Migration `0004_auth_user_email_unique_ci.py`

### Tradeoffs / Catatan
- Resend verifikasi disembunyikan setelah signup untuk mencegah enumeration
- User masih bisa melakukan resend setelah login
- Cookies di-prod menggunakan setting keamanan ketat (HTTPS strict)
- Migration email unique akan gagal jika ada duplikat email → harus dibersihkan dulu
- Lockout per-IP efektif mengurangi brute force, namun serangan terdistribusi tetap memerlukan rate limit di layer edge (nginx/cloudflare)

## [1.4.3] - 2026-05-19
### Summary
Pembaruan UI halaman `/project` menjadi project hub dengan tampilan notebook yang lebih rapi. Perubahan ini masih sebatas antarmuka; aksi buat, buka, dan menu item belum terhubung ke fitur backend.

### Changed
- `templates/project.html`: mengganti layout lama menjadi grid notebook, empty state visual, dan header yang lebih fokus ke workspace.
- `templates/base.html`: navbar dibuat mengikuti tipe halaman, termasuk avatar ringkas di halaman project.
- `accounts/context_processors.py` dan `config/settings.py`: menambahkan context processor navbar agar template bisa membedakan tampilan home, project, dan auth.
- `config/views.py`: menghapus flag navbar manual dari view project karena kontrol tampilan pindah ke context processor.

### Notes
- UI baru ini masih placeholder untuk alur kerja project; interaksi data dan aksi tombol belum aktif.


## [1.4.2] - 2026-05-16
### Summary
Penerapan SMTP menggunakan Bervo untuk pengiriman email (verifikasi & reset).

### Added
- Konfigurasi SMTP Bervo di `config/settings.py` (env vars: `BERVO_*`).
- Utilitas pengiriman email di `accounts/utils.py` menggunakan Bervo.

### Changed
- Pengiriman email verifikasi dan reset diarahkan ke Bervo SMTP.

## [1.4.1] - 2026-05-16
### Summary
Implementasi reusable loading button helper untuk meningkatkan UX saat submit form.

### Added
- `components.js`: Helper reusable `data-loading-button` untuk tombol loading state.

### Changed
- Menambahkan loading button behavior pada halaman:
  - `signin.html`
  - `signup.html`
  - `forgot_password.html`
  - `email_unverified.html`
  - `password_reset_confirm.html`

### Features
- Tombol otomatis disable saat proses berjalan
- Label tombol berubah menjadi teks loading (bisa dikustom via `data-loading-text`)
- Mudah digunakan di tombol lain cukup dengan menambahkan atribut `data-loading-button`

## [1.4.0] - 2026-05-14

### Summary
Perbaikan signifikan pada Authentication Flow dan keamanan verifikasi email.

### Changed
- **Auth Flow** telah diperbaiki dan di-hardening:
  - Tidak lagi menyimpan raw email di session `email_unverified` maupun endpoint `resend_verification`
  - Menghapus lookup status akun berdasarkan query string atau body email (mencegah informasi bocor)
  - Menghapus auto-resend email verifikasi saat login user yang belum verified
  - Signup & Login sekarang hanya menyimpan akun unverified ke session (lebih aman)
  - Password reset di-throttle berdasarkan IP dan cooldown per akun
  - Logout dan verifikasi email sekarang membersihkan session pending verification

### Files Changed
- `accounts/views.py`
- `accounts/utils.py`
- `accounts/tests.py`
- `templates/auth/email_unverified.html`

## [1.3.0] - 2026-05-13

### Summary
Implementasi pembersihan otomatis akun unverified yang expired.

### Added
- `accounts/management/commands/cleanup_unverified_users.py`: Management command untuk membersihkan user inactive yang belum verifikasi email.

### Changed
- Sistem cleanup unverified users:
  - Menghapus user dengan `is_active=False` dan `email_verified=False` yang melebihi batas waktu.
  - Default cutoff: 24 jam sejak `date_joined`.

### Features
- Mode `--dry-run` untuk preview tanpa menghapus data
- Opsi `--days` untuk mengatur masa tenggang
- Batch processing untuk performa yang baik
- Logging lengkap dan safety confirmation
- Command idempotent dan aman dijalankan berkali-kali

### Notes
- Hanya menghapus akun yang memang belum pernah verifikasi email
- Siap dijadwalkan via cron job untuk maintenance rutin
- Mendukung konfigurasi di masa depan (misalnya 72 jam)


## [1.2.2] - 2026-05-13

### Summary
Perbaikan dan peningkatan sistem verifikasi email.

### Changed
- `accounts/views.py`: Signup user sekarang langsung inactive.
- `accounts/views.py`: Link verifikasi dapat mengaktifkan user sekaligus menandai profile sebagai verified.
- `accounts/forms.py`  dan `accounts/views.py` : Login memblokir user inactive dengan pesan yang jelas, serta otomatis mengirim ulang email verifikasi jika cooldown sudah lewat.
- `templates/auth/email_verification_invalid.html` (line 7): Pesan untuk link expired/used diperbarui.
- `accounts/tests.py` : Test diupdate sesuai lifecycle verifikasi email yang baru.

### Notes
- Error "Email atau domain email tidak valid" sekarang muncul dengan benar di toast notification.

## [1.1.3] - 2026-05-13

### Summary
- Error `Email atau domain email tidak valid` muncul di toast.

### Changed
- `accounts/views.py`: Perbaikan pesan error validasi email agar lebih user-friendly dan muncul di toast.


## [1.2.1] - 2026-05-13

### Summary
email verification hardening

### Added
- `accounts/validator.py`:  untuk memeriksa cooldown pengiriman email verifikasi.
  
### Changed
- `accounts/forms.py`: Implementasi validasi email dengan memanggil fungsi validator.
- `requirements.txt`: email-validator ditambahkan sebagai dependensi untuk validasi email yang lebih robust.


## [1.2.0] - 2026-05-13

### Summary
Docker setup telah selesai dikonfigurasi untuk development dan production.

### Added
- `Dockerfile`
- `docker-compose.yml`
- `.dockerignore`

### Changed
- `config/settings.py`: Menambahkan support `DATABASE_URL` dan dynamic `ALLOWED_HOSTS`
- `README.md`: 
  - Menambahkan panduan instalasi & menjalankan via Docker
  - Mengganti referensi worker dari Celery menjadi RQ

## [1.1.1] - 2026-05-11

### Added
- Environment variable loading via `python-dotenv` di `settings.py` (GOOGLE_OAUTH_CLIENT_ID kini terbaca saat Django start).
- Test regresi untuk Google OAuth: memastikan user baru terbentuk dengan benar dan `email_verified` ikut terset.
- Konfigurasi `SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin-allow-popups'`.

### Changed
- Perbaikan alur Google OAuth di `views.py`:
  - User baru dibuat tanpa `create_user()`.
  - Password dibuat `unusable` (bukan empty string).
  - Login sekarang menggunakan backend eksplisit `django.contrib.auth.backends.ModelBackend`.
- `ALLOWED_HOSTS` dipersempit ke `localhost` dan `127.0.0.1`.

### Files Changed
- `config/settings.py`
- `accounts/views.py`
- `accounts/tests.py`

### Notes
- Helper yang tidak terpakai di `accounts/views.py` dapat dibersihkan lebih lanjut (opsional).

## [1.1.0] - 2026-05-11

### Fixed
- Perbaikan Google OAuth 400 `origin_mismatch` dengan penambahan konfigurasi `Authorized JavaScript origins` pada Google Cloud Console (frontend URL seperti `http://localhost:8000`, `http://wsl.localhost:8000`, `http://localhost:5173`).
- Penyesuaian backend: variabel `FRONTEND_URL` ditambahkan ke `CSRF_TRUSTED_ORIGINS` secara otomatis, serta validasi `aud` pada auth Google dipastikan sesuai dengan `GOOGLE_OAUTH_CLIENT_ID`.

### Changed
- Login diubah dari username/email menjadi **email only**:
  - Form login sekarang hanya menerima email + password.
  - Penghapusan validasi unique username (signup tidak lagi memiliki field username).
  - Penambahan auth backend email-only.
- Database:
  - Kolom `auth_user.username` menjadi nullable dan tidak unique (constraint unique dihapus).
  - Migrasi baru: `accounts/migrations/0003_auth_user_username_nullable_not_unique.py`.
- Frontend:
  - `signin.html`: input berubah menjadi email only.
  - `signup.html`: field username dihapus.
  - `auth-validation.js`: aturan validasi username dihapus.

### Files Changed
- `config/settings.py`
- `accounts/forms.py`
- `accounts/views.py`
- `accounts/utils.py`
- `accounts/backends.py`
- `templates/signin.html`
- `templates/signup.html`
- `static/js/auth-validation.js`

### Notes
- Migrasi database telah berhasil dijalankan di WSL dengan perintah `./venv/bin/python manage.py migrate`. Skema terverifikasi: kolom username sudah NULLable dan indeks unique telah dihapus.
- Pastikan Client ID yang digunakan UI sesuai dengan `GOOGLE_OAUTH_CLIENT_ID` di environment.

## [1.0.6] - 2026-05-11

### Changed
- Pembaruan template autentikasi dan halaman utama.
- Perubahan CSS/JS: `static/css/theme.css`, `static/js/toast.js`.
- Penyesuaian `config/settings.py`.
- Menambah aset gambar/SVG (untracked).



## [1.0.5] - 2026-05-07

### Summary
- Penguatan alur autentikasi: verifikasi email tanpa auto-login, pembatasan kirim ulang email, rate limit Google OAuth, dan hardening template/frontend.

### Added
- `accounts/migrations/0002_userprofile_last_verification_email_sent_at.py`: Menambah field `last_verification_email_sent_at` pada `UserProfile` untuk melacak cooldown kirim ulang email verifikasi.

### Changed / Added (analisis per file)
- `CHANGELOG.md`: Memuat ringkasan rilis ini dalam bahasa Indonesia dan analisis perubahan per file.

- `accounts/models.py`: Menambahkan field timestamp untuk dukungan rate limit verifikasi email.
- `accounts/tests.py`: Memperbarui ekspektasi alur autentikasi dan menambah tes untuk cooldown resend serta token verifikasi sekali pakai.
- `accounts/utils.py`: Menambah generator token verifikasi khusus, pembatasan kirim ulang email, serta rate limit untuk endpoint Google OAuth.
- `accounts/views.py`: Mengubah `sign_up` agar tidak auto-login, mengarahkan verifikasi ke halaman login, menerapkan cooldown resend, rate limit Google login, dan logout saat verifikasi berhasil.
- `config/settings.py`: Menambahkan konfigurasi `PASSWORD_RESET_TIMEOUT` agar token reset password punya batas waktu.
- `static/js/auth-validation.js`: Menambah sanitasi input frontend dengan trim otomatis saat submit dan blur.
- `templates/auth/_google_oauth.html`: Meng-escape `GOOGLE_OAUTH_CLIENT_ID` saat dirender ke atribut HTML.
- `templates/auth/email_unverified.html`: Menambah tombol resend dengan data cooldown dan countdown UI di sisi klien.
- `templates/base.html`: Meng-escape tag pesan agar data flash lebih aman saat dipindah ke variabel JavaScript.
- `templates/forgot_password.html`: Meng-escape error form agar output lebih aman.
- `templates/project.html`: Meng-escape username dan email pengguna pada halaman proyek.
- `templates/signin.html`: Meng-escape pesan error form pada halaman login.
- `templates/signup.html`: Meng-escape pesan error form pada halaman daftar.



### Notes
- Verifikasi end-to-end tetap perlu diuji: pengiriman email, invalidasi token lama, cooldown resend, dan Google OAuth rate limit.


## [1.0.4] - 2026-05-06

### Added
- Infrastruktur AI Agent di `.ai_agent/` dengan folder `skills/` untuk plugin changelog generator dan komponen AI lainnya.
- File `AGENTS.md` untuk konfigurasi dan dokumentasi AI Agent.

## [1.0.3] - 2026-05-06

### Added
- Dokumentasi autentikasi lengkap: `doc/AUTH.md` (penjelasan alur sign up, sign in, verifikasi email, reset password, Google OAuth, rate-limiting, dan komponen terkait).
- Halaman proyek `templates/project.html` dan penyesuaian landing page pada `templates/home.html`.

### Changed
- Pembaruan views dan routing autentikasi di `config/views.py` dan `config/urls.py` untuk mendukung flows sign in, sign up, forgot password, verifikasi email, dan Google OAuth.
- Template autentikasi diperbarui: `templates/signin.html`, `templates/signup.html`, `templates/forgot_password.html` serta `templates/base.html` untuk menampilkan flash messages dan CTA dinamis.

### Notes
- Beberapa direktori dan file terkait autentikasi (`accounts/`, `templates/auth/`) ditambahkan/diubah; tinjau implementasi lebih lanjut untuk integrasi penuh.


## [1.0.2] - 2026-05-05

### Added
- Implementasi authentication views di `config/views.py` untuk sign_in, sign_up, dan forgot_password dengan validasi data.
- Template `templates/signin.html` untuk halaman login dengan form email/username dan password.
- Template `templates/signup.html` untuk halaman pendaftaran dengan field username, email, password, dan konfirmasi password.
- Template `templates/forgot_password.html` untuk halaman reset password dengan input email.
- Routes baru di `config/urls.py` untuk `/signin/`, `/signup/`, dan `/forgot-password/`.

### Changed
- Navbar di `templates/base.html` kini dinamis dengan context `hide_nav` untuk menyembunyikan navbar pada halaman autentikasi.
- Routing di `config/urls.py` diubah dari TemplateView menjadi function-based views.

## [1.0.1] - 2026-05-04

### Added
- Menambahkan folder `doc/` untuk dokumentasi pengembangan.
- Menambahkan aset CSS: `static/css/theme.css` dan `static/css/typography.css` .

### Changed
- Memperbarui `package.json` dan `package-lock.json` untuk menyelaraskan dependensi frontend.
- Memperbarui `static/css/input.css` untuk menyesuaikan tema dan utilitas CSS.
- Memperbarui template `templates/base.html` dan `templates/home.html` (landing page) 
- 
### Removed
- Menghapus `tailwind.config.js` sebagai bagian dari restrukturisasi tooling frontend.

### Notes
- Direktori `static/svg/` saat ini belum dilacak; pertimbangkan menambahkannya jika dibutuhkan oleh rilis berikutnya.

## [1.0.0] - 2026-05-01

### Added
- Inisialisasi baseline proyek Django 5 dengan konfigurasi template, static files, halaman root, dan routing admin agar repo punya fondasi yang bisa langsung dijalankan dan diverifikasi di lingkungan WSL.
- Setup integrasi `django-rq` beserta command `rqworker` kustom agar antrian background siap dipakai saat alur pemrosesan dokumen mulai diimplementasikan.
- Tooling frontend berbasis Tailwind, PostCSS, Flowbite, Marked, dan Mermaid agar antarmuka awal serta kebutuhan render markdown dan diagram sudah tersedia sejak awal pengembangan.
- Halaman `home.html` untuk development check yang memverifikasi template, asset JavaScript, dan endpoint penting tanpa perlu menunggu fitur utama selesai dibangun.
- Dokumentasi arsitektur di `Architecture.md` dan panduan perubahan di `CHANGELOG_RULE.md` agar arah implementasi, pembagian modul, dan aturan dokumentasi perubahan jelas sejak initial commit.

### Fixed
- Compatibility wrapper untuk worker RQ pada rilis `rq` yang lebih baru, sehingga command worker tetap dapat dijalankan walau API lama `rq.Connection` tidak lagi diekspor.