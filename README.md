# 📚 MythosNote

Sistem AI-powered note-taking yang memungkinkan pengguna mengelola workspace, mengunggah dokumen, dan berinteraksi dengan AI berdasarkan konteks dokumen.

**Stack:** Python (Django) | PostgreSQL | Redis | Supabase Storage | Gemini/OpenAI/DeepSeek API

---

## 📋 Daftar Isi

- [Fitur Utama](#fitur-utama)
- [Prasyarat Sistem](#prasyarat-sistem)
- [Setup untuk Windows](#setup-untuk-windows)
- [Setup untuk WSL (Windows Subsystem for Linux)](#setup-untuk-wsl)
- [Setup untuk Linux/macOS](#setup-untuk-linuxmacos)
- [Setup untuk Docker](#setup-untuk-docker)
- [Konfigurasi Environment](#konfigurasi-environment)
- [Menjalankan Aplikasi](#menjalankan-aplikasi)
- [Struktur Project](#struktur-project)
- [API Endpoints](#api-endpoints)
- [Troubleshooting](#troubleshooting)

---

## 🎉 Terbaru (v1.4.12+)

**Perubahan signifikan:**
- ✨ Migrasi storage dari Google Cloud Storage ke **Supabase Storage**
- ✨ Workspace quota system dengan limit 10 workspace per user
- ✨ Race condition fixes untuk atomic workspace creation
- ✨ Chat API dengan RAG (Retrieval-Augmented Generation)
- ✨ Generate API untuk async content generation (ringkasan, kuis, tabel, mindmap)
- ✨ Backend support untuk multiple AI providers (Gemini, OpenAI, DeepSeek)
- ✨ Embedding providers dengan 768-dimensional vectors
- ✨ UI improvements dengan modal-based workspace management & toast notifications

Lihat [CHANGELOG.md](CHANGELOG.md) untuk detail lengkap semua perubahan.

---

## ✨ Fitur Utama

- ✅ **Manajemen Workspace**: Kelola multiple workspace (max 10 per user), create/rename/delete
- ✅ **Upload Dokumen**: Support PDF/DOCX/TXT dengan ekstraksi teks otomatis
- ✅ **AI Chat RAG**: Interaksi dengan AI berdasarkan konteks dokumen (Retrieval-Augmented Generation)
- ✅ **Generate Content**: Auto-generate ringkasan, tabel, kuis, mindmap via background jobs
- ✅ **Semantic Search**: Pencarian menggunakan embedding vectors (768-dimensional)
- ✅ **Cloud Storage**: Penyimpanan dokumen di Supabase Storage
- ✅ **Multi-AI Provider**: Support Gemini, OpenAI, DeepSeek
- ✅ **Rate Limiting**: Proteksi API dengan quota harian per user
- ✅ **Background Processing**: RQ worker untuk ekstraksi & embedding async

---

## 🔧 Prasyarat Sistem

### Requirement Dasar (Semua Platform)
- **Python 3.9+** ([Download](https://www.python.org/downloads/))
- **Git** ([Download](https://git-scm.com/))
- **PostgreSQL 12+** (database)
- **Redis 6+** (cache)
- **Node.js 20+** (untuk Tailwind CSS watch/build)
- **pip** (Python package manager - included dengan Python)

### Akun & API Keys
- Akun **Supabase** (untuk file storage)
- API Key **Gemini**, **OpenAI**, atau **DeepSeek** (pilih minimal satu)

---

## 🪟 Setup untuk Windows (Pemula-Friendly)

### Step 1: Install Python & Git (Download Langsung)

#### 1.1 Install Python
1. Kunjungi [python.org/downloads](https://www.python.org/downloads/)
2. Download **Python 3.11 atau lebih baru** (Windows installer)
3. Buka file `.exe` yang didownload
4. **⚠️ PENTING**: Centang **"Add Python to PATH"** di bagian bawah (jangan lupa!)
5. Klik "Install Now" dan tunggu sampai selesai
6. Klik "Close" saat selesai

#### 1.2 Verifikasi Python
Buka **Command Prompt** (tekan `Win + R`, ketik `cmd`, tekan Enter):
```bash
python --version
# Harus menampilkan Python 3.11+ (bukan error)
```
Jika error, ulangi step 1.1 dan pastikan "Add Python to PATH" terchecklist.

#### 1.3 Install Git
1. Kunjungi [git-scm.com](https://git-scm.com/download/win)
2. Download **Git for Windows** (arsitektur 64-bit)
3. Buka file `.exe` dan ikuti installer (semua default settings OK)
4. Setelah selesai, buka **Command Prompt baru** dan verifikasi:
```bash
git --version
```

### Step 2: Install PostgreSQL & Redis

#### Opsi A: Installer Windows (Recommended untuk Pemula)

**PostgreSQL:**
1. Download dari [postgresql.org/download/windows](https://www.postgresql.org/download/windows/)
2. Pilih versi **15 atau lebih baru**
3. Buka installer dan lakukan setup:
   - Default location: OK
   - **Password untuk user "postgres"**: Simpan dengan aman! Contoh: `admin123`
   - Port: 5432 (default) - OK
   - Locale: Indonesia - OK
4. Finish & jangan run Stack Builder

**Redis:**
1. Download dari [github.com/microsoftarchive/redis/releases](https://github.com/microsoftarchive/redis/releases)
2. Pilih **Redis-x64-xxx.msi**
3. Buka installer dan pilih "Install Redis as a Windows Service" (important!)
4. Finish

#### Opsi B: Menggunakan Chocolatey (Untuk Advanced Users)
```bash
# Buka Command Prompt sebagai Administrator (klik kanan → Run as Administrator)
choco install postgresql redis-64
```

### Step 3: Verifikasi Instalasi

Buka **Command Prompt** dan jalankan:
```bash
python --version        # Harus menampilkan 3.11+
git --version          # Harus menampilkan git version
psql --version         # Harus menampilkan psql version
redis-cli --version    # Harus menampilkan redis_version
```

Jika ada yang error, ulangi step 1-2 untuk tool tersebut.

### Step 4: Clone Project & Setup Python Environment

1. Buka **Command Prompt** dan navigate ke folder yang diinginkan:
```bash
# Contoh: Desktop
cd %USERPROFILE%\Desktop

# atau Dokumen
cd %USERPROFILE%\Documents
```

2. Clone repository:
```bash
git clone https://github.com/IbnuSabilGitHub/MythosNote.git
cd MythosNote
```

3. Buat virtual environment:
```bash
python -m venv venv
```

4. **Aktivasi virtual environment**:
```bash
# Untuk Command Prompt:
venv\Scripts\activate

# Untuk PowerShell:
venv\Scripts\Activate.ps1
```

> 💡 Setelah aktivasi, prompt akan berubah jadi `(venv) C:\...>`

5. Install dependencies:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 5: Setup Database PostgreSQL

1. Buka **pgAdmin** (aplikasi yang sudah ter-install bersama PostgreSQL)
   - Atau buka CMD dan ketik: `psql -U postgres`

2. Jika menggunakan **psql** (Command Prompt):
```bash
# Masukkan password postgres yang Anda set di Step 2
psql -U postgres
```

3. Jalankan command SQL berikut (dalam psql prompt):
```sql
CREATE USER mythosnote_user WITH PASSWORD 'your_secure_password';
CREATE DATABASE mythosnote OWNER mythosnote_user;
\q
```

4. Verifikasi:
```bash
psql -U mythosnote_user -d mythosnote -h localhost
# Jika bisa login, ketik \q untuk exit
```

### Step 6: Setup Environment Variables (.env)

1. Buka **Notepad** atau **VS Code**
2. Buka file `.env.example` dari project MythosNote
3. Copy semua isi dan save sebagai `.env` di folder MythosNote
4. Edit `.env` dan isi dengan konfigurasi Anda:

```bash
# DJANGO
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# DATABASE (ganti password sesuai Step 5)
DATABASE_URL=postgresql://mythosnote_user:your_secure_password@localhost:5432/mythosnote

# REDIS
REDIS_URL=redis://localhost:6379/0

# EMAIL (development mode)
EMAIL_MODE=console
DEFAULT_FROM_EMAIL=no-reply@mythosnote.local

# SUPABASE STORAGE
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-key
SUPABASE_BUCKET=your-bucket-name

# AI PROVIDER (pilih salah satu: gemini, openai, deepseek)
AI_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-api-key

# RATE LIMITING
MAX_PROMPTS_PER_DAY=50
MAX_GENERATES_PER_DAY=20
```

> ⚠️ **Jangan commit `.env` ke Git!** Sudah ada di `.gitignore`

### Step 7: Migrate Database

Pastikan virtual environment masih aktif, lalu:
```bash
python manage.py migrate
```

Anda akan melihat banyak output "Running migrations..." sampai selesai.

### Step 8: Buat Admin Account

```bash
python manage.py createsuperuser
# Ikuti prompt: username, email, password (ketik password, tidak akan terlihat)
```

Contoh:
```
Username: admin
Email: admin@example.com
Password: 
(Tidak akan terlihat saat mengetik)
Password (again): 
Superuser created successfully.
```

### Step 9: Jalankan Aplikasi

Buka **3 terminal Command Prompt** terpisah, semua di folder MythosNote:

**Terminal 1 - Django Server:**
```bash
venv\Scripts\activate
python manage.py runserver
# Output: Starting development server at http://127.0.0.1:8000/
```

**Terminal 2 - Redis Server:**
```bash
redis-server
# Jika sudah diinstall sebagai Windows Service, bisa skip ini
```

**Terminal 3 - RQ Worker (untuk background jobs):**
```bash
venv\Scripts\activate
python manage.py rqworker default
```

✅ **Aplikasi sudah siap!** Akses di: `http://localhost:8000`

✅ **Admin panel:** `http://localhost:8000/admin` (login dengan akun dari Step 8)

---

## 🐧 Setup untuk WSL (Windows Subsystem for Linux)

### Step 1: Setup WSL2
```bash
# Buka PowerShell sebagai Administrator
wsl --install
wsl --set-default-version 2

# Restart komputer, kemudian setup Ubuntu
```

### Step 2: Update & Install Dependencies
```bash
# Update package manager
sudo apt update && sudo apt upgrade -y

# Install Python & dependencies
sudo apt install -y python3 python3-pip python3-venv python3-dev git

# Install PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Install Redis
sudo apt install -y redis-server

# Install Node.js 20+ (nvm)
curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
source ~/.bashrc
nvm install 20
nvm use 20

# Verifikasi
python3 --version
psql --version
redis-cli --version
node --version
```

Catatan: jika `nvm` belum terbaca, jalankan ulang:
```bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
```

### Step 3: Start Services
```bash
# Start PostgreSQL
sudo service postgresql start

# Start Redis
sudo service redis-server start

# Verifikasi PostgreSQL running
sudo service postgresql status
```

### Step 4: Setup PostgreSQL User & Database
```bash
# Login sebagai postgres user
sudo -u postgres psql

# Jalankan commands berikut di psql prompt:
CREATE USER mythosnote_user WITH PASSWORD 'your_secure_password';
CREATE DATABASE mythosnote OWNER mythosnote_user;
ALTER ROLE mythosnote_user SET client_encoding TO 'utf8';
ALTER ROLE mythosnote_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE mythosnote_user SET default_transaction_deferrable TO on;
ALTER ROLE mythosnote_user SET default_transaction_level TO 'committed';
GRANT ALL PRIVILEGES ON DATABASE mythosnote TO mythosnote_user;
\q

# Verifikasi
psql -U mythosnote_user -d mythosnote -h localhost -c "SELECT version();"
```

Catatan: jika muncul error "Peer authentication failed", jalankan:
```bash
sudo -u postgres psql -c "CREATE USER mythosnote_user WITH PASSWORD 'your_secure_password';"
sudo -u postgres psql -c "CREATE DATABASE mythosnote OWNER mythosnote_user;"
```

### Step 5: Clone & Setup Project
```bash
# Clone repository
git clone https://github.com/IbnuSabilGitHub/MythosNote.git
cd MythosNote

# Buat virtual environment
python3 -m venv venv

# Aktifkan virtual environment
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 6: Setup Environment Variables
```bash
# Copy .env.example ke .env
cp .env.example .env

# Edit .env dengan nano atau vim
nano .env
# Isi dengan konfigurasi Anda, tekan Ctrl+O untuk save, Ctrl+X untuk exit
```

### Step 7: Run Database Migrations
```bash
python manage.py migrate
```

### Step 8: Create Superuser
```bash
python manage.py createsuperuser
# Ikuti prompt untuk membuat admin account
```

### Step 9: Jalankan Development Server
```bash
# Dalam WSL terminal
python manage.py runserver 0.0.0.0:8000
```

✅ Akses dari Windows: `http://localhost:8000`
✅ Admin panel: `http://localhost:8000/admin`

---

## 🍎 Setup untuk Linux/macOS

### Step 1: Install Dependencies
```bash
# macOS (menggunakan Homebrew)
brew install python@3.11 postgresql redis git

# Linux (Ubuntu/Debian)
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv python3-dev git postgresql postgresql-contrib redis-server

# Install Node.js 20+ (nvm) untuk Linux
curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
source ~/.bashrc
nvm install 20
nvm use 20
```

### Step 2: Start Services
```bash
# Linux: Start PostgreSQL & Redis
sudo systemctl start postgresql
sudo systemctl start redis-server

# macOS: Services sudah auto-start via Homebrew
```

Catatan: di WSL (tanpa systemd), gunakan:
```bash
sudo service postgresql start
sudo service redis-server start
```

### Step 3: Setup Database
```bash
# Login ke PostgreSQL
sudo -u postgres psql

# Jalankan di psql prompt:
CREATE USER mythosnote_user WITH PASSWORD 'your_secure_password';
CREATE DATABASE mythosnote OWNER mythosnote_user;
ALTER ROLE mythosnote_user SET client_encoding TO 'utf8';
ALTER ROLE mythosnote_user SET default_transaction_isolation TO 'read committed';
\q
```

### Step 4: Clone & Setup Project
```bash
git clone https://github.com/IbnuSabilGitHub/MythosNote.git
cd MythosNote

python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

### Step 5: Setup Environment Variables
```bash
cp .env.example .env
# Edit .env dengan text editor favorit
nano .env
```

### Step 6: Database & Superuser
```bash
python manage.py migrate
python manage.py createsuperuser
```

### Step 7: Run Server
```bash
python manage.py runserver
```

✅ Akses: `http://localhost:8000`

---

## 🐳 Setup untuk Docker

### Prasyarat
- Install Docker Desktop atau Docker Engine + Docker Compose.
- Pastikan file `.env` sudah ada. Cara paling cepat: copy dari `.env.example`.

### Step 1: Siapkan environment
```bash
cp .env.example .env
```

### Step 2: Jalankan stack
```bash
docker compose up --build
```

### Step 3: Buat superuser
```bash
docker compose exec web python manage.py createsuperuser
```

### Service yang ikut jalan
- `web`: Django app di `http://localhost:8000`
- `db`: PostgreSQL
- `redis`: Redis untuk RQ
- `worker`: RQ worker

Catatan: `docker compose` akan override `DATABASE_URL` dan `REDIS_URL` supaya memakai service internal `db` dan `redis`.

---

## ⚙️ Konfigurasi Environment

### File `.env` - Penjelasan Detail

```bash
# DJANGO
SECRET_KEY=your-secret-key-here
# Generate dengan: python manage.py shell
# >>> from django.core.management.utils import get_random_secret_key
# >>> print(get_random_secret_key())

DEBUG=True
# Set False untuk production

ALLOWED_HOSTS=localhost,127.0.0.1,yourdomain.com
# Tambah domain production Anda

# DATABASE
DATABASE_URL=postgresql://mythosnote_user:your_secure_password@localhost:5432/mythosnote
# Format: postgresql://username:password@host:port/database

# REDIS
REDIS_URL=redis://localhost:6379/0
# Untuk production: redis://:password@host:port/db

# EMAIL
EMAIL_MODE=console
# Pilihan: console/development, smtp, brevo
DEFAULT_FROM_EMAIL=no-reply@mythosnote.local
EMAIL_ASYNC=false

# BREVO SMTP
# EMAIL_MODE=brevo
# DEFAULT_FROM_EMAIL=no-reply@yourdomain.com
# BREVO_SMTP_USER=your-brevo-smtp-login
# BREVO_SMTP_KEY=your-brevo-smtp-key
# BREVO_SMTP_HOST=smtp-relay.brevo.com
# BREVO_SMTP_PORT=587
# BREVO_SMTP_USE_TLS=true

# SMTP GENERIK
# EMAIL_MODE=smtp
# EMAIL_HOST=smtp.example.com
# EMAIL_PORT=587
# EMAIL_USE_TLS=true
# EMAIL_USE_SSL=false
# EMAIL_HOST_USER=your-smtp-user
# EMAIL_HOST_PASSWORD=your-smtp-password

# SUPABASE STORAGE (untuk file upload)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
SUPABASE_BUCKET=mythosnote-bucket

# AI PROVIDER
AI_PROVIDER=gemini  # atau 'openai', 'deepseek'
GEMINI_API_KEY=your-gemini-api-key
OPENAI_API_KEY=your-openai-api-key
DEEPSEEK_API_KEY=your-deepseek-api-key
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1

# EMBEDDING PROVIDER
EMBEDDING_PROVIDER=openai  # atau 'gemini'
EMBEDDING_MODEL=text-embedding-3-small

# RATE LIMITING
MAX_PROMPTS_PER_DAY=50
MAX_GENERATES_PER_DAY=20
```

### Setup Email SMTP

Project memakai `EMAIL_MODE` agar mudah pindah mode tanpa ubah kode.

#### Development
```bash
EMAIL_MODE=console
DEFAULT_FROM_EMAIL=no-reply@mythosnote.local
```

Email dicetak ke console terminal. Alias yang juga valid: `EMAIL_MODE=development`.

#### Brevo
```bash
EMAIL_MODE=brevo
DEFAULT_FROM_EMAIL=no-reply@yourdomain.com
BREVO_SMTP_USER=your-brevo-smtp-login
BREVO_SMTP_KEY=your-brevo-smtp-key
BREVO_SMTP_HOST=smtp-relay.brevo.com
BREVO_SMTP_PORT=587
BREVO_SMTP_USE_TLS=true
```

Langkah setup Brevo:
1. Login ke dashboard Brevo.
2. Buka **SMTP & API**.
3. Copy SMTP login ke `BREVO_SMTP_USER`, bukan `smtp-relay.brevo.com`.
4. Generate SMTP key, lalu isi `BREVO_SMTP_KEY`.
5. Pastikan sender/domain sudah verified.
6. Set `DEFAULT_FROM_EMAIL` memakai sender yang verified.

#### SMTP generik
```bash
EMAIL_MODE=smtp
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_USE_SSL=false
EMAIL_HOST_USER=your-smtp-user
EMAIL_HOST_PASSWORD=your-smtp-password
DEFAULT_FROM_EMAIL=no-reply@yourdomain.com
```

#### Test kirim email
```bash
python manage.py shell
```

```python
from django.core.mail import send_mail
send_mail("SMTP test", "Email MythosNote aktif.", None, ["you@example.com"])
```

### Mendapatkan API Keys & Setup Storage

#### Supabase Storage (untuk file upload)
1. Daftar di [supabase.com](https://supabase.com)
2. Buat project baru
3. Di menu "Storage", buat bucket baru (nama: `mythosnote-bucket`)
4. Copy `Project URL` → `SUPABASE_URL`
5. Copy `anon key` dari Settings → API → Anon → `SUPABASE_KEY`

#### OpenAI API
1. Daftar di [openai.com](https://platform.openai.com)
2. Buat API key di Settings → API Keys
3. Set `OPENAI_API_KEY`

#### Gemini API
1. Dapatkan di [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Copy API key ke `GEMINI_API_KEY`

#### DeepSeek API
1. Dapatkan di [DeepSeek Platform](https://platform.deepseek.com/)
2. Buat API key di API Keys
3. Copy API key ke `DEEPSEEK_API_KEY`
4. Set `DEEPSEEK_BASE_URL=https://api.deepseek.com/v1`

---

## 🚀 Menjalankan Aplikasi

### Development Mode
```bash
# Aktifkan virtual environment
source venv/bin/activate  # Linux/macOS
# atau
venv\Scripts\activate  # Windows

# Terminal 1: Django Server
python manage.py runserver

# Terminal 2: Redis (jika tidak auto-start)
redis-server

# Terminal 3: RQ Worker (untuk async tasks)
python manage.py rqworker default

# Terminal 4: RQ Scheduler
python manage.py rqworker default --with-scheduler
```

### Collect Static Files
```bash
python manage.py collectstatic --noinput
```

### Create Test Data
```bash
python manage.py shell < fixtures/create_test_data.py
```

### Check Status
```bash
# Verifikasi database
python manage.py dbshell

# Verifikasi dependencies
pip list

# Jalankan tests
python manage.py test
```

---

## 📂 Struktur Project

```
MythosNote/
├── manage.py                 # Django management script
├── requirements.txt          # Python dependencies
├── .env.example             # Environment template
├── README.md                # Dokumentasi (ini)
│
├── mythosnote/              # Main Django project
│   ├── settings.py          # Konfigurasi utama
│   ├── urls.py              # URL routing
│   ├── wsgi.py              # Production server config
│   └── rqworker.py          # RQ worker compatibility command
│
├── apps/
│   ├── accounts/             # Authentication & user management
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── forms.py
│   │   ├── signals.py       # User signal handlers
│   │   └── urls.py
│   │
│   ├── workspaces/          # Workspace management
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── utils.py         # Workspace quota logic
│   │   └── urls.py
│   │
│   └── sources/             # Document/source handling
│       ├── models.py        # Source, SourceChunk models
│       ├── views.py         # Upload, list, delete endpoints
│       ├── tasks.py         # RQ background jobs (extraction, embedding)
│       ├── embeddings.py    # Embedding providers (OpenAI, Gemini)
│       ├── providers.py     # Chat providers (Gemini, OpenAI, DeepSeek)
│       ├── serializers.py
│       └── urls.py
│
├── static/                  # Static files (CSS, JS)
│   ├── css/
│   ├── js/
│   └── img/
│
├── templates/               # HTML templates
│   ├── base.html
│   ├── workspace/
│   ├── document/
│   └── ai/
│
└── fixtures/                # Initial data
    └── create_test_data.py
```

---

## 🔌 API Endpoints

### Workspace Management
- `GET /api/workspaces/` - List all workspaces (per user)
- `POST /api/workspaces/` - Create new workspace (max 10 per user)
- `GET /api/workspaces/{id}/` - Workspace detail
- `PUT /api/workspaces/{id}/rename/` - Rename workspace (max 40 chars)
- `DELETE /api/workspaces/{id}/` - Delete workspace

### Sources (Dokumen)
- `GET /api/sources/` - List sources (dokumen) per workspace
- `POST /api/sources/upload/` - Upload file source (PDF/DOCX/TXT, max 20MB)
- `GET /api/sources/{id}/` - Source detail
- `GET /api/sources/{id}/status/` - Check processing status
- `DELETE /api/sources/{id}/` - Delete source & file

### AI Chat (RAG-based)
- `POST /api/workspaces/{id}/chat/` - Chat dengan konteks dokumen
  - Input: `{"message": "pertanyaan", "workspace_id": "xxx"}`
  - Output: AI response berdasarkan source chunks

### Generate Content (Async Jobs)
- `POST /api/workspaces/{id}/generate/` - Trigger generate job
  - Input: `{"action": "summarize|quiz|mindmap|table"}`
  - Output: `{"id": "job_id", "status": "queued"}`
- `GET /api/jobs/{job_id}/status/` - Check job status

### Authentication
- `POST /api/auth/login/` - User login
- `POST /api/auth/register/` - User registration
- `POST /api/auth/logout/` - User logout
- `POST /api/auth/refresh/` - Refresh token
- `POST /api/auth/email-verify/` - Verify email address

---

## 🐛 Troubleshooting

### Error: "psql: command not found"
```bash
# Windows: Tambah PostgreSQL ke PATH
# C:\Program Files\PostgreSQL\15\bin\

# WSL/Linux:
sudo apt install postgresql-client
```

### Error: "Redis connection refused"
```bash
# Pastikan Redis running
redis-cli ping
# Response: PONG

# Jalankan Redis:
redis-server  # Linux/macOS
redis-server.exe  # Windows
```

### Error: "System has not been booted with systemd"
```bash
sudo service postgresql start
sudo service redis-server start
```

### Error: "ModuleNotFoundError"
```bash
# Update pip & reinstall requirements
pip install --upgrade pip
pip install -r requirements.txt
```

### Error: "Permission denied" di Linux/WSL
```bash
sudo chown -R $USER:$USER .
chmod -R u+rwx .
```

### Database Connection Error
```bash
# Verifikasi credentials di .env
psql -U mythosnote_user -d mythosnote -h localhost

# Cek PostgreSQL running
sudo service postgresql status  # Linux/WSL
pg_isready  # All platforms
```

### Port 8000 sudah digunakan
```bash
# Gunakan port lain:
python manage.py runserver 8080

# Atau kill process yang menggunakan port 8000:
# Windows: netstat -ano | findstr :8000
# Linux: lsof -i :8000 | kill -9 <PID>
```

### Virtual Environment Corrupt
```bash
# Delete dan recreate
rm -rf venv  # Linux/macOS
rmdir /s venv  # Windows CMD

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 📚 Dokumentasi Tambahan

- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [django-rq Documentation](https://django-rq.readthedocs.io/)
- [PostgreSQL Tutorial](https://www.postgresql.org/docs/current/tutorial.html)
- [Supabase Documentation](https://supabase.com/docs)
- [Gemini API](https://ai.google.dev/tutorials/get_started_web)
- [OpenAI API](https://platform.openai.com/docs)
- [DeepSeek API](https://platform.deepseek.com/)

---

## 📝 Changelog

Lihat [CHANGELOG.md](CHANGELOG.md) untuk daftar lengkap perubahan, fitur baru, dan perbaikan di setiap versi.

---

## 📝 Lisensi

Project ini menggunakan lisensi [MIT License](LICENSE)

---

## 👨‍💻 Kontribusi

Kontribusi selalu diterima! Silakan:
1. Fork repository
2. Buat feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push ke branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

---

## 📧 Support

Pertanyaan atau isu? Hubungi:
- **GitHub Issues**: [MythosNote Issues](https://github.com/IbnuSabilGitHub/MythosNote/issues)
- **Email**: [Your Email]

---

**Happy Coding! 🚀**

*Last Updated: 2026-05-07*
## Cleanup unverified users

Hapus akun signup yang tetap `is_active=False` dan `email_verified=False` setelah 24 jam:

```bash
./venv/bin/python manage.py cleanup_unverified_users --dry-run
./venv/bin/python manage.py cleanup_unverified_users --no-confirm
```

Cron contoh harian:

```cron
0 3 * * * cd /home/mypc/projects/MythosNote && ./venv/bin/python manage.py cleanup_unverified_users --no-confirm >> /var/log/mythosnote-cleanup.log 2>&1
```
