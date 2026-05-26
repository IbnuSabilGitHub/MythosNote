# Project Context: MythosNote

## 1. Project Overview

MythosNote is an AI-powered note-taking platform (NotebookLM-style): users manage workspaces, upload documents, and chat with AI over document context. **Current codebase state (v1.4.6):** production-ready **session-based authentication** and marketing/project UI; core workspace, upload, RAG, and REST APIs are **planned or stubbed** (models exist for sources; workspaces app missing).

- **Django:** 5.0.1 | **Python:** 3.12+ (venv uses 3.12.3)
- **Database:** PostgreSQL recommended (with **pgvector** for planned embeddings); SQLite fallback when `DATABASE_URL` unset
- **Key libraries** (`requirements.txt`): Django, djangorestframework (not wired), django-cors-headers (not wired), django-rq, psycopg2-binary, pgvector, PyMuPDF, google-cloud-storage, python-dotenv, requests, gunicorn, email-validator

---

## 2. Architecture & Project Structure

```
MythosNote/
├── config/                 # Django project (settings, urls, wsgi, root views)
├── apps/
│   ├── accounts/           # CUSTOM — auth, profiles, usage, email, RQ email jobs
│   └── sources/            # CUSTOM — models only (NOT in INSTALLED_APPS yet)
├── templates/              # Django templates (base, auth, home, project)
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
| `config/` | Custom | Settings, URL routing, `home` / `project` views |
| `apps/accounts/` | Custom | Auth flows, `UserProfile`, `UserUsage`, signals, management commands |
| `apps/sources/` | Custom (inactive) | `Source`, `SourceChunk` models; no app config/migrations/views |
| `django.contrib.*` | Third-party | Admin, auth User, sessions, messages, staticfiles |
| `django_rq` | Third-party | Queue dashboard + worker integration |

**Not present in repo:** `apps/workspaces/`, API views, source processing workers, GCS upload handlers (described in `README.md` / `Architecture.md` as roadmap).

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

### `sources.Source` [NOT ACTIVE — not migrated / not in INSTALLED_APPS]

- **Purpose:** Uploaded source files per workspace (RAG pipeline).
- **Fields:** UUID PK; `user`, `workspace` FK; `original_filename`, `mime_type`, `file_size`, `storage_path`; `status` (pending|queued|processing|ready|failed); `error_message`, `progress` 0–100; timestamps.
- **FK:** `user -> User`; `workspace -> workspaces.Workspace` **[NOT FOUND — app missing]**
- **Meta:** `unique_together (workspace, original_filename)`; indexes on `(workspace, status)`, `(user, created_at)`; ordering `-created_at`.

### `sources.SourceChunk` [NOT ACTIVE]

- **Purpose:** Text chunks + vector embeddings for semantic search.
- **Fields:** UUID PK; `source` FK; `chunk_index`, `text_content`, `token_count`; `embedding: VectorField(null=True)` (pgvector); `metadata: JSONField`.
- **Meta:** `unique_together (source, chunk_index)`; index `(source, chunk_index)`.

---

## 4. Endpoints

**No JSON REST API** is implemented (`djangorestframework` not in `INSTALLED_APPS`). All routes return HTML unless noted.

### Public / project

```
GET  /
Auth: optional
Output: HTML landing (home.html)
Files: config.views.home

GET  /project/
Auth: required + verified email (@verified_email_required)
Output: HTML project hub (UI only; notebook actions not wired)
Files: config.views.project
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

### Admin / ops

```
GET  /admin/          # Django admin (UserProfile, UserUsage)
GET  /django-rq/      # django-rq dashboard (staff access per Django admin)
```

**Planned (README, not implemented):** `/api/workspace/`, source upload, chat — [NOT FOUND in code].

---

## 5. Background Tasks (RQ / Redis)

| Task | Location | Trigger | Input | Side effects | Errors |
|------|----------|---------|-------|--------------|--------|
| `_send_mail_job` | `apps/accounts/utils.py` | `_dispatch_email()` when `EMAIL_ASYNC=true` | subject, message, recipients, from_email, html_message | Sends email via Django mail backend | Enqueue failure → **sync fallback** + warning log |
| Source processing | [NOT FOUND] | Planned on upload | — | Chunk + embed + GCS | — |

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
- **Multi-tenant:** **[NOT IMPLEMENTED]** Planned: workspace-scoped data (`Source.workspace`). Decorator `verified_email_required` gates future workspace/core features.
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
SESSION/CSRF cookie security (strict when not DEBUG)
SECURE_SSL_REDIRECT, HSTS, etc.
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
GCS_BUCKET_NAME
GCS_PROJECT_ID
GOOGLE_APPLICATION_CREDENTIALS
GOOGLE_OAUTH_CLIENT_ID
AI_PROVIDER
GEMINI_API_KEY
OPENAI_API_KEY
EMBEDDING_MODEL
MAX_PROMPTS_PER_DAY
MAX_GENERATES_PER_DAY
FRONTEND_URL
SESSION_COOKIE_SECURE, CSRF_COOKIE_SECURE, etc. (optional overrides)
```

**In requirements but unused in settings:** `EMBEDDING_PROVIDER`, DRF, CORS — [ASSUMPTION: wired when API layer lands].

---

## 8. Frontend Conventions

- **Templates:** Django templates under `templates/`; `DIRS` includes project `templates/`, `APP_DIRS=True`.
- **Inheritance:** `base.html` → page templates (`home.html`, `project.html`, `signin.html`, …); auth emails under `templates/auth/emails/`.
- **CSS:** Tailwind CSS v4 — source `static/css/input.css` → built `static/css/output.css` via `npm run build:css`; theme in `theme.css`, `typography.css`.
- **JavaScript:** Vanilla JS modules (`static/js/components.js`, `toast.js`, `messages.js`, `auth-validation.js`); **Flowbite** 4.x for dropdowns; **Iconify** CDN; **marked** + **mermaid** (CDN) for future markdown/diagrams; **AOS** in package.json (optional).
- **HTMX / Alpine:** [NOT FOUND]
- **Google OAuth:** partial `templates/auth/_google_oauth.html`; disabled UI if `GOOGLE_OAUTH_CLIENT_ID` empty.
- **Context processors:** `auth_settings` (OAuth client id, verification flag), `navbar_config` (`show_navbar`, `navbar_type`: home | project | default).
- **Language:** UI copy largely Indonesian (`id` on `<html>`).

---

## 9. File Storage

- **Current settings:** Local static only (`STATIC_URL`, `STATIC_ROOT`, `STATICFILES_DIRS`). **MEDIA_URL / MEDIA_ROOT:** [NOT FOUND in settings].
- **Planned (`.env.example`, `Source.storage_path`, README):** Google Cloud Storage; path pattern like `workspaces/{id}/sources/{filename}` [ASSUMPTION: matches Architecture.md].
- **Static:** `/static/` → `static/` dev, `staticfiles/` collectstatic; SVG logos, images under `static/img/`.

---

## 10. Testing

- **Framework:** Django `TestCase` (`apps/accounts/tests.py` — `AuthFlowTests`); **pytest:** [NOT FOUND configured].
- **Strategy:** `@override_settings` with locmem email, relaxed cookie security; integration tests for signup, verify, login lockout, resend throttle, Google user creation, cleanup command.
- **Coverage:** No enforced threshold in repo; `.ai_agent` docs mention 80%+ as goal [ASSUMPTION].
- **DB:** Default test DB (SQLite in-memory or configured engine).

---

## 11. Deployment Notes

- **Docker Compose:** `db` (Postgres 16), `redis` (7), `web` (migrate + runserver :8000), `worker` (`rqworker default`); `DATABASE_URL` and `REDIS_URL` injected.
- **Dockerfile:** Node 20 + Python 3 (Debian); `pip install -r requirements.txt`, `npm install`, `npm run build:css`; default CMD migrate + runserver (use gunicorn in production [ASSUMPTION]).
- **Migrations:** `python manage.py migrate` on deploy; accounts migrations 0001–0004; **sources:** no migrations yet.
- **pgvector:** Enable extension on Postgres before activating `sources` app [ASSUMPTION per README].
- **RQ:** Separate worker process/container required when `EMAIL_ASYNC=true` or future document jobs.
- **Production checklist:** Set `DEBUG=false`, `SECRET_KEY`, Postgres `DATABASE_URL`, Redis, email (Brevo/SMTP), `GOOGLE_OAUTH_CLIENT_ID`, GCS credentials when upload ships; run `cleanup_unverified_users` via cron if desired.

---

## Quick Reference for AI Agents

| Topic | Status |
|-------|--------|
| Auth / sessions | **Done** |
| `/project/` UI | **Done** (no backend CRUD) |
| Workspaces app | **Missing** |
| Sources app (DB) | **Models only** |
| REST `/api/*` | **Missing** |
| RAG / embeddings / GCS | **Missing** (deps present) |
| AI chat | **Missing** |

When extending the project: register new apps under `apps/`, add to `INSTALLED_APPS`, include URLs in `config/urls.py`, reuse `@verified_email_required` for user-facing features, and scope data by `workspace_id` once `workspaces` exists.
