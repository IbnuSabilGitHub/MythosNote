# Project Context: MythosNote

## 1. Project Overview

MythosNote is an AI-powered note-taking platform (NotebookLM-style): users manage workspaces, upload documents, and chat with AI over document context. **Current codebase state (v1.2.37):** production-ready **session-based authentication**, full **workspace management** (CRUD), **source upload, polling & processing APIs** (supporting PDF, TXT, MD, DOCX), **dynamic workspace dashboard UI**, fully implemented **RAG retrieval pipeline** (cosine distance search via pgvector), dynamic **frontend chat UI** with source filtering and counter badge, **chat persistence** (session and message logging), and complete migration to **Gemini/DeepSeek** (OpenAI fully removed).

- **Django:** 5.0.1 | **Python:** 3.12+ (venv uses 3.12.3)
- **Database:** PostgreSQL recommended (with **pgvector** for embeddings); SQLite fallback when `DATABASE_URL` unset
- **Key libraries** (`requirements.txt`): Django, djangorestframework ✅ **wired**, django-rq, psycopg2-binary, pgvector, PyMuPDF, python-docx, supabase (unused), python-dotenv, requests, gunicorn, email-validator, google-genai

---

## 2. Architecture & Project Structure

```
MythosNote/
├── config/                 # Django project (settings, urls, wsgi, root views)
├── apps/
│   ├── accounts/           # CUSTOM — auth, profiles, usage, email, RQ email jobs
│   ├── workspaces/         # CUSTOM — workspace CRUD, quota, models ✅ ACTIVE
│   └── sources/            # CUSTOM — upload, delete, chat, generate, embeddings ✅ ACTIVE
├── templates/              # Django templates (base, auth, home, project, workspace)
├── static/                 # CSS (Tailwind build), JS, SVG, images
├── doc/                    # AUTH.md, DESIGN.md (reference docs)
├── manage.py
├── requirements.txt
├── package.json            # Tailwind v4 build
├── docker-compose.yml
└── Dockerfile
```

| Path | Type | Purpose |
|------|------|---------|
| `config/` | Custom | Settings, URL routing, `home` / `project` / `workspace` views; REST config |
| `apps/accounts/` | Custom | Auth flows, `UserProfile`, `UserUsage`, signals, management commands |
| `apps/workspaces/` | Custom ✅ **active** | `Workspace` model, CRUD views, quota logic, rate limiting |
| `apps/sources/` | Custom ✅ **active** | `Source`, `SourceChunk`, `GenerateJob`, `ChatSession`, `ChatMessage` models; upload, delete, status, chat, generate views |
| `django.contrib.*` | Third-party | Admin, auth User, sessions, messages, staticfiles |
| `rest_framework` | Third-party | REST API framework ✅ **in INSTALLED_APPS** |
| `django_rq` | Third-party | Queue dashboard + worker integration |

**Active features:** Standard Local FileStorage (FileSystemStorage) with media_data shared Docker volumes, Gemini Embedding Provider (`gemini-embedding-001` via `google-genai` SDK), pgvector RAG flow, dynamic AI chat & generate with DeepSeek and Gemini.

---

## 3. Database Schema (Critical Models)

### `auth.User` (Django built-in — email-centric identity)

- **Purpose:** Primary user account; email is the login identifier.
- **Customizations (migrations):** `username` nullable, non-unique; case-insensitive unique index on `LOWER(email)` where email non-empty (`auth_user_email_ci_unique`).
- **Sign-up:** `is_active=False` until email verification; Google users may get `username=None`, unusable password.

### `accounts.UserProfile`

- **Purpose:** Email verification state separate from `User.is_active`.
- **Fields:**
  ```
  user: OneToOneField(AUTH_USER_MODEL, CASCADE, related_name="profile")
  email_verified: BooleanField(default=False)
  last_verification_email_sent_at: DateTimeField(null=True)  # resend cooldown
  created_at, updated_at: DateTimeField(auto)
  ```
- **FK:** `user -> User`
- **Meta:** none beyond defaults; created via `post_save` signal on User create.

### `accounts.UserUsage`

- **Purpose:** Daily counters for failed logins and (planned) AI prompt/generate quotas.
- **Fields:**
  ```
  user: ForeignKey(User, null=True, CASCADE, related_name="usage_records")
  identifier: CharField(255)  # e.g. "email|ip" bucket for anonymous/login tracking
  ip_address: GenericIPAddressField(null=True)
  date: DateField
  prompt_count, generate_count: PositiveIntegerField(default=0)  # reserved for AI limits
  failed_login_count: PositiveIntegerField(default=0)
  failed_login_window_started_at, last_failed_login_at: DateTimeField(null=True)
  ```
- **Constraints:** `UniqueConstraint(user, identifier, date)` — `unique_user_usage_per_identifier_day`
- **Indexes:** `(date, identifier)`, `(date, user)`

### `workspaces.Workspace` ✅ **ACTIVE**

- **Purpose:** User workspace container for sources and chat sessions.
- **Fields:** UUID PK; `user` FK; `name` (max 40 chars); `created_at`, `updated_at` (auto timestamps).
- **FK:** `user -> User`
- **Meta:** ordering `-created_at`; index on `(user, created_at)`.
- **Quota:** max 10 workspaces per user; enforced in views.

### `sources.Source` ✅ **ACTIVE**

- **Purpose:** Uploaded source files per workspace (RAG pipeline).
- **Fields:** UUID PK; `user`, `workspace` FK; `original_filename`, `mime_type`, `file_size`, `storage_path`; `status` (pending|queued|processing|ready|failed); `extracted_text` (TEXT); `error_message`, `progress` 0–100; timestamps.
- **FK:** `user -> User`; `workspace -> workspaces.Workspace` ✅
- **Meta:** `unique_together (workspace, original_filename)`; indexes on `(workspace, status)`, `(user, created_at)`; ordering `-created_at`.

### `sources.SourceChunk` ✅ **ACTIVE**

- **Purpose:** Text chunks + vector embeddings for semantic search.
- **Fields:** UUID PK; `source` FK; `chunk_index`, `text_content`, `token_count`; `embedding: VectorField(null=True)` (pgvector); `metadata: JSONField`.
- **Meta:** `unique_together (source, chunk_index)`; index `(source, chunk_index)`; ordering `chunk_index`.

### `sources.GenerateJob` ✅ **ACTIVE**

- **Purpose:** Async generation jobs (summary, mindmap, quiz, table) from workspace sources.
- **Fields:** UUID PK; `user`, `workspace` FK; `action` (summary|mindmap|quiz|table); `status` (queued|processing|success|failed); `result` (TEXT); `error_message`; `created_at`, `updated_at`.
- **FK:** `user -> User`; `workspace -> workspaces.Workspace`
- **Meta:** ordering `-created_at`; indexes on `(workspace, status)`, `(user, created_at)`.

### `sources.ChatSession` ✅ **ACTIVE**

- **Purpose:** AI chat session container inside a workspace.
- **Fields:** UUID PK; `user` and `workspace` FKs; `title` (max 120 chars); `created_at`, `updated_at`.
- **Meta:** ordering `-updated_at`; indexes on `(workspace, updated_at)` and `(user, created_at)`.

### `sources.ChatMessage` ✅ **ACTIVE**

- **Purpose:** Individual message inside a ChatSession (user query or assistant reply).
- **Fields:** UUID PK; `session` FK; `role` (user|assistant); `content` (TEXT); `metadata` (JSONField); `created_at`, `updated_at`.
- **Meta:** ordering `created_at`; indexes on `(session, created_at)` and `(session, role)`.

---

## 4. Endpoints

**REST API implemented** (`djangorestframework` ✅ in `INSTALLED_APPS`). HTML-based views coexist with JSON API endpoints.

### Public / project

```
GET  /
Auth: optional
Output: HTML landing (home.html)
Files: config.views.home

GET  /project/
Auth: required + verified email (@verified_email_required)
Output: HTML workspace dashboard (Workspace CRUD UI)
Files: config.views.project

GET  /workspace/?workspace_id=<uuid>
Auth: required + verified email (@verified_email_required)
Output: HTML workspace detail (sources, chat, generate)
Files: config.views.workspace
```

### Authentication (`apps.accounts.urls`)

```
GET|POST  /signin/
Auth: guest only (@guest_required)
Input: email, password
Output: HTML or redirect home / email-unverified
Errors: wrong credentials, rate limit, inactive account → email-unverified
Files: apps.accounts.views.sign_in

GET|POST  /signup/
Auth: guest
Input: email, password, password_confirm (MX-validated email)
Output: redirect email-unverified; generic message (anti-enumeration)
Files: apps.accounts.views.sign_up

POST  /auth/google/
Auth: guest
Input: credential (Google ID token)
Output: redirect home or email-unverified
Errors: missing credential, validation failure, rate limit, duplicate email
Files: apps.accounts.views.google_sign_in

GET|POST  /forgot-password/
Auth: guest
Input: email
Output: always generic success message; email if active user (rate limited)
Files: apps.accounts.views.forgot_password

GET|POST  /reset/<uidb64>/<token>/
Auth: guest
Input: new password (POST)
Output: HTML confirm or invalid token page
Files: apps.accounts.views.password_reset_confirm

GET  /email-unverified/
Auth: optional (session-bound pending user or logged-in unverified)
Output: HTML gate; resend hidden after generic signup confirmation
Files: apps.accounts.views.email_unverified

POST  /resend-verification/
Auth: session/login-bound target user
Output: redirect email-unverified; 5 min cooldown per user
Files: apps.accounts.views.resend_verification

GET  /verify-email/<uidb64>/<token>/
Auth: none
Output: activate user, set email_verified; redirect signin (logs out if was logged in)
Errors: invalid/expired token page
Files: apps.accounts.views.verify_email

POST  /logout/
Auth: any
Output: redirect home
Files: apps.accounts.views.sign_out
```

### Workspace API ✅ **ACTIVE**

```
POST   /api/workspaces/<uuid:id>/rename/
Auth: required (IsAuthenticated)
Input: {"name": "New Name"}
Output: {"id": "<uuid>", "name": "New Name"}  [200 OK]
RateLimit: 60 per 60s per user, 5 min per-request cooldown
Files: apps.workspaces.views.WorkspaceRenameView

DELETE /api/workspaces/<uuid:id>/
Auth: required
Output: [204 No Content]
RateLimit: same as rename
Files: apps.workspaces.views.WorkspaceDeleteView
```

### Sources API ✅ **ACTIVE**

```
GET    /api/sources/?workspace_id=<uuid>
Auth: required
Output: [{"id", "workspace_id", "original_filename", "status", ...}, ...]
Files: apps.sources.views.SourceListView

POST   /api/sources/upload/
Auth: required
Input: multipart/form-data {file, workspace_id}
Output: {"id", "status", "progress", ...}  [201 Created]
Files: apps.sources.views.SourceUploadView

DELETE /api/sources/<uuid:id>/
Auth: required
Output: [204 No Content]
Files: apps.sources.views.SourceDeleteView

GET    /api/sources/<uuid:id>/status/
Auth: required
Output: {"id", "status", "progress", "chunks": [...]}
Files: apps.sources.views.SourceStatusView
```

### Chat & Generate API ✅ **ACTIVE**

```
POST   /api/workspace/<uuid:id>/chat/
Auth: required
Input: {"message": "...", "session_id": "<uuid>", "source_ids": [...]}
Output: {"message": "...", "response": "...", "sources": [{"id", "original_filename"}, ...], "created_at": "...", "session_id": "..."}
Files: apps.sources.views.ChatView

GET    /api/workspace/<uuid:id>/chat/sessions/
Auth: required
Output: [{"id", "title", "created_at", "updated_at"}, ...]
Files: apps.sources.views.ChatSessionListView

GET    /api/workspace/<uuid:session_id>/chat/messages/
Auth: required
Output: [{"id", "role", "content", "created_at"}, ...]
Files: apps.sources.views.ChatMessageListView

DELETE /api/workspace/<uuid:id>/chat/messages/
Auth: required
Output: [204 No Content]
Files: apps.sources.views.ChatMessageDeleteView

POST   /api/workspace/<uuid:id>/generate/
Auth: required
Input: {"action": "summary|mindmap|quiz|table"}
Output: {"generate_job": {"id": "<uuid>", "status": "queued"}}
Files: apps.sources.views.GenerateView
```

### Admin / ops

```
GET  /admin/          # Django admin (UserProfile, UserUsage, Workspace, Source, SourceChunk, GenerateJob)
GET  /django-rq/      # django-rq dashboard (staff access per Django admin)
```

---

## 5. Background Tasks (RQ / Redis)

| Task | Location | Trigger | Input | Side effects | Status |
|------|----------|---------|-------|--------------|--------|
| `_send_mail_job` | `apps/accounts/utils.py` | `_dispatch_email()` when `EMAIL_ASYNC=true` | subject, message, recipients, from_email, html_message | Sends email via Django mail backend | ✅ Active |
| `process_source` | `apps/sources/tasks.py` | Source upload API | source_id | Extract text, chunk, embed, store chunks in DB | ✅ Implemented |
| `process_generate_job` | `apps/sources/tasks.py` | GenerateJob creation | job_id, prompt | Generate summary/mindmap/quiz/table (provider-specific) | ✅ Implemented |

- **Queue:** `default` (`RQ_QUEUES` in settings; `REDIS_URL` or localhost:6379).
- **Worker:** `python manage.py rqworker default` or Docker `worker` service; custom `apps.accounts.management.commands.rqworker` mirrors django-rq for rq API compatibility.
- **Management:** `cleanup_unverified_users` — deletes inactive, unverified users older than `UNVERIFIED_USER_CLEANUP_DAYS` (default 1); supports `--dry-run`, `--batch-size`, confirm prompt.

---

## 6. Authentication & Authorization

- **Auth method:** **Django session** (cookies). No JWT/API tokens in use.
- **User model:** `django.contrib.auth.models.User` (default `AUTH_USER_MODEL`; not swapped).
- **Login:** `apps.accounts.backends.EmailBackend` — email + password; timing-safe dummy hash on unknown email; only `is_active=True` users authenticate via backend (inactive caught in `SignInForm`).
- **Google:** Google Identity Services → POST credential → `verify_google_credential()` (tokeninfo API) → `get_or_create_google_user()`.
- **Email verification:** `UserProfile.email_verified` + `User.is_active`; custom `EmailVerificationTokenGenerator`; verification link in email.
- **Multi-tenant:** ✅ **Implemented** — workspace-scoped data via `Source.workspace` and `ChatSession.workspace` FK. Decorator `@verified_email_required` gates workspace/core features. Workspaces enforce user ownership in queries.
- **Decorators:**
  - `@guest_required` — redirect authenticated users to `home`
  - `@verified_email_required` — login + verified email for protected pages (e.g. `/project/`)
- **Session keys:** `pending_verification_user_id`, `signup_verification_submitted`
- **Rate limits:** failed login (5 / 15 min per usage row), verification resend (5 min), Google OAuth (10 / 5 min per IP, cache), password reset (5 / 5 min per IP + 300s per-user cooldown, cache)

---

## 7. Configuration & Settings

Non-default / env-driven (`config/settings.py`):

```
SECRET_KEY          # required
DEBUG               # default false
ALLOWED_HOSTS       # comma-separated
DATABASE_URL        # postgres/postgresql/sqlite; else sqlite db.sqlite3
REDIS_URL           # optional; else localhost:6379
RQ_QUEUES           # default queue, timeout 360s
FRONTEND_URL        # CSRF_TRUSTED_ORIGINS if set
AUTHENTICATION_BACKENDS = EmailBackend + ModelBackend
LOGIN_URL = 'signin', LOGIN_REDIRECT_URL = 'home'
EMAIL_MODE          # console | smtp | brevo
EMAIL_ASYNC         # enqueue mail via RQ
UNVERIFIED_USER_CLEANUP_DAYS
GOOGLE_OAUTH_CLIENT_ID
REST_FRAMEWORK      # SessionAuthentication, IsAuthenticated permission class
SESSION/CSRF cookie security (strict when not DEBUG)
SECURE_SSL_REDIRECT, HSTS, etc.
MEDIA_URL, MEDIA_ROOT  # local file storage (dev/prod shared volume)
```

**Environment variables** (from `.env.example`; values not stored in repo):

```
SECRET_KEY
DEBUG
ALLOWED_HOSTS
DATABASE_URL
REDIS_URL
EMAIL_MODE
DEFAULT_FROM_EMAIL
EMAIL_ASYNC
BREVO_SMTP_* (if brevo)
EMAIL_HOST, EMAIL_PORT, EMAIL_* (if smtp)
GOOGLE_OAUTH_CLIENT_ID
AI_PROVIDER
GEMINI_API_KEY
DEEPSEEK_API_KEY
DEEPSEEK_BASE_URL
EMBEDDING_MODEL
MAX_PROMPTS_PER_DAY
MAX_GENERATES_PER_DAY
FRONTEND_URL
SESSION_COOKIE_SECURE, CSRF_COOKIE_SECURE, etc. (optional overrides)
```

**In requirements but partially used in settings:** `django-cors-headers` (not in MIDDLEWARE yet; reserved for future cross-origin API); `EMBEDDING_PROVIDER` env var reserved for embedding provider selection.

---

## 8. Frontend Conventions

- **Templates:** Django templates under `templates/`; `DIRS` includes project `templates/`, `APP_DIRS=True`.
- **Inheritance:** `base.html` → page templates (`home.html`, `project.html` [Workspace Dashboard], `workspace.html` [Workspace detail with sources], `signin.html`, …); auth emails under `templates/auth/emails/`; modals in `templates/components/`.
- **CSS:** Tailwind CSS v4 — source `static/css/input.css` → built `static/css/output.css` via `npm run build:css`; theme in `theme.css`, `typography.css`.
- **JavaScript:** Vanilla JS modules (`static/js/project.js`, `auth/validation.js`, `toast/manager.js`, `ui/loading-button.js`, `workspace/index.js`, `workspace/layout.js`, `workspace/selection.js`, `workspace/sources.js`, `workspace/chat.js`); **Flowbite** 4.x for dropdowns; **Iconify** CDN; **marked** + **mermaid** (CDN) for markdown/diagrams; **AOS** in package.json (optional).
- **HTMX / Alpine:** [NOT FOUND]
- **Google OAuth:** partial `templates/auth/_google_oauth.html`; disabled UI if `GOOGLE_OAUTH_CLIENT_ID` empty.
- **Context processors:** `auth_settings` (OAuth client id, verification flag), `navbar_config` (`show_navbar`, `navbar_type`: home | project | default); additional view-level context: `workspace_quota` (count, limit, remaining, can_create), `workspace_name_max_length`, `active_workspace` (workspace detail views).
- **Language:** UI copy largely Indonesian (`id` on `<html>`).

---

## 9. File Storage

- **Current settings:** Local file storage (dev/prod): `STATIC_URL=/static/`, `STATIC_ROOT=static/`, `MEDIA_URL=/media/`, `MEDIA_ROOT=media/`; source uploads stored locally with path `workspaces/{workspace_id}/sources/{filename}` using standard Django `default_storage` (FileSystemStorage).
- **Shared Volume:** Shared Docker volume (`media_data` mounted under `MEDIA_ROOT` in both `web` and `worker` services) ensures uploaded files are accessible by asynchronous worker jobs for text extraction.
- **Supabase Storage:** Unused/Migrated back to local FileSystemStorage.

---

## 10. Testing

- **Framework:** Django `TestCase` (`apps/accounts/tests.py` — `AuthFlowTests`); **pytest:** [NOT FOUND configured].
- **Strategy:** `@override_settings` with locmem email, relaxed cookie security; integration tests for signup, verify, login lockout, resend throttle, Google user creation, cleanup command.
- **Coverage:** No enforced threshold in repo; `.ai_agent` docs mention 80%+ as goal [ASSUMPTION].
- **DB:** Default test DB (SQLite in-memory or configured engine).

---

## 11. Deployment Notes

- **Docker Compose:** `db` (Postgres 16), `redis` (7), `web` (migrate + runserver :8000), `worker` (`rqworker default`); `DATABASE_URL` and `REDIS_URL` injected. Shared volume `media_data` handles media file sync.
- **Dockerfile:** Node 20 + Python 3 (Debian); `pip install -r requirements.txt`, `npm install`, `npm run build:css`; default CMD migrate + runserver (use gunicorn in production [ASSUMPTION]).
- **Migrations:** `python manage.py migrate` on deploy; accounts migrations 0001–0004; workspaces 0001_initial; sources 0001–0003 (Source, SourceChunk, GenerateJob, ChatSession, ChatMessage models).
- **pgvector:** Enable extension on Postgres before activating `sources` app [ASSUMPTION per README].
- **RQ:** Separate worker process/container required when `EMAIL_ASYNC=true` or future document jobs.
- **Production checklist:** Set `DEBUG=false`, `SECRET_KEY`, Postgres `DATABASE_URL`, Redis, email (Brevo/SMTP), `GOOGLE_OAUTH_CLIENT_ID`; when deploying embeddings/chat: set AI provider API keys (Gemini/DeepSeek); run `cleanup_unverified_users` via cron if desired.

---

## Quick Reference for AI Agents

| Topic | Status |
|-------|--------|
| Auth / sessions | **✅ Done** |
| Workspace Dashboard (`/project/`) | **✅ Done** (Create, Rename, Delete) |
| Workspaces app | **✅ Active** (model, views, quota, rate limit) |
| Sources app (DB) | **✅ Active** (models, views, upload/delete/status endpoints) |
| REST `/api/*` | **✅ Done** (workspace/source/chat/generate CRUD & async) |
| RAG / embeddings / Storage | **✅ Done** (Gemini embeddings, standard FileSystemStorage, pgvector) |
| AI chat / generate | **✅ Done** (dynamic frontend chat, source filtering, Gemini & DeepSeek integration) |

When extending the project: register new apps under `apps/`, add to `INSTALLED_APPS`, include URLs in `config/urls.py`, reuse `@verified_email_required` for user-facing features, scope data by `workspace_id`, and follow workspace quota patterns for multi-tenant constraints.

## Migration to Gemini/DeepSeek

Fully migrated embedding and chat capabilities to Gemini and DeepSeek. 
- **OpenAI Fully Removed**: The OpenAI Python SDK dependency and all OpenAI providers (embedding/chat) have been deleted.
- **Gemini Embeddings**: Powered by the `google-genai` SDK and model `gemini-embedding-001` (768 dimensions), utilizing exponential backoff retry logic. `LocalEmbeddingProvider` acts as a local fallback placeholder.
- **AI Providers**: Configurable via `AI_PROVIDER` as either `gemini` or `deepseek` with respective environment variables (`GEMINI_API_KEY`, `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`).
