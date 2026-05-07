# 📚 MythosNote

Sistem AI-powered note-taking yang memungkinkan pengguna mengelola workspace, mengunggah dokumen, dan berinteraksi dengan AI berdasarkan konteks dokumen.

**Stack:** Python (Django) | PostgreSQL | Redis | Google Cloud Storage | Gemini/OpenAI API

---

## 📋 Daftar Isi

- [Fitur Utama](#fitur-utama)
- [Prasyarat Sistem](#prasyarat-sistem)
- [Setup untuk Windows](#setup-untuk-windows)
- [Setup untuk WSL (Windows Subsystem for Linux)](#setup-untuk-wsl)
- [Setup untuk Linux/macOS](#setup-untuk-linuxmacos)
- [Konfigurasi Environment](#konfigurasi-environment)
- [Menjalankan Aplikasi](#menjalankan-aplikasi)
- [Struktur Project](#struktur-project)
- [API Endpoints](#api-endpoints)
- [Troubleshooting](#troubleshooting)

---

## ✨ Fitur Utama

- ✅ Manajemen Workspace: Kelola multiple workspace dalam satu akun
- ✅ Upload Dokumen: Support berbagai format file (PDF, DOCX, TXT, etc)
- ✅ AI Chat: Interaksi dengan AI berdasarkan konteks dokumen
- ✅ Semantic Search: Pencarian dokumen menggunakan embedding
- ✅ Rate Limiting: Proteksi API dengan pembatasan request harian
- ✅ Cloud Storage: Penyimpanan dokumen di Google Cloud Storage
- ✅ Multi-AI Provider: Support Gemini dan OpenAI

---

## 🔧 Prasyarat Sistem

### Requirement Dasar (Semua Platform)
- **Python 3.9+** ([Download](https://www.python.org/downloads/))
- **Git** ([Download](https://git-scm.com/))
- **PostgreSQL 12+** (database)
- **Redis 6+** (cache)
- **pip** (Python package manager - included dengan Python)

### Akun & API Keys
- Akun **Google Cloud Platform** (untuk GCS & Gemini API)
- API Key **Gemini** atau **OpenAI** (pilih satu atau keduanya)

---

## 🪟 Setup untuk Windows

### Step 1: Install Python & Git
1. Download Python dari [python.org](https://www.python.org/downloads/)
   - ✅ Centang "Add Python to PATH" saat install
2. Download & install Git dari [git-scm.com](https://git-scm.com/)

### Step 2: Install PostgreSQL & Redis

#### Opsi A: Menggunakan Chocolatey (Recommended)
```bash
# Install Chocolatey terlebih dahulu (run as Administrator)
# https://chocolatey.org/install

choco install postgresql redis-64
```

#### Opsi B: Download Manual
- PostgreSQL: [postgresql.org/download/windows](https://www.postgresql.org/download/windows/)
- Redis: [microsoftarchive.github.io/redis](https://microsoftarchive.github.io/redis/releases)

### Step 3: Verifikasi Instalasi
```bash
python --version
git --version
psql --version
redis-cli --version
```

### Step 4: Clone & Setup Project
```bash
# Clone repository
git clone https://github.com/IbnuSabilGitHub/MythosNote.git
cd MythosNote

# Buat virtual environment
python -m venv venv

# Aktifkan virtual environment
# Untuk Command Prompt:
venv\Scripts\activate
# Atau untuk PowerShell:
venv\Scripts\Activate.ps1

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 5: Setup Database
```bash
# Buka Command Prompt sebagai Administrator
# Buat database user
psql -U postgres -c "CREATE USER mythosnote_user WITH PASSWORD 'your_secure_password';"

# Buat database
psql -U postgres -c "CREATE DATABASE mythosnote OWNER mythosnote_user;"

# Verifikasi
psql -U postgres -l
```

### Step 6: Setup Environment Variables
```bash
# Copy .env.example ke .env
copy .env.example .env

# Edit .env dengan text editor (Notepad++ recommended)
# Isi dengan konfigurasi Anda
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
# Terminal 1: Django Development Server
python manage.py runserver

# Terminal 2: Redis Server (jika menggunakan Windows native Redis)
redis-server

# Terminal 3: Celery Worker (untuk async tasks)
celery -A mythosnote worker -l info
```

✅ Akses aplikasi di: `http://localhost:8000`
✅ Admin panel: `http://localhost:8000/admin`

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

# Verifikasi
python3 --version
psql --version
redis-cli --version
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
psql -U mythosnote_user -d mythosnote -c "SELECT version();"
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
```

### Step 2: Start Services
```bash
# Linux: Start PostgreSQL & Redis
sudo systemctl start postgresql
sudo systemctl start redis-server

# macOS: Services sudah auto-start via Homebrew
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

# EMAIL (Optional untuk dev)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
# Production: django.core.mail.backends.smtp.EmailBackend
DEFAULT_FROM_EMAIL=no-reply@mythosnote.local

# GOOGLE CLOUD
GCS_BUCKET_NAME=your-bucket-name
GCS_PROJECT_ID=your-gcp-project-id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
# Download dari GCP Console

# AI PROVIDER
AI_PROVIDER=gemini  # atau 'openai'
GEMINI_API_KEY=your-gemini-api-key
OPENAI_API_KEY=your-openai-api-key

# EMBEDDING
EMBEDDING_MODEL=text-embedding-3-small

# RATE LIMITING
MAX_PROMPTS_PER_DAY=50
MAX_GENERATES_PER_DAY=20
```

### Mendapatkan API Keys

#### Google Cloud (GCS & Gemini)
1. Buat project di [Google Cloud Console](https://console.cloud.google.com/)
2. Enable: Cloud Storage API, Gemini API
3. Buat Service Account & download JSON key
4. Set `GOOGLE_APPLICATION_CREDENTIALS` ke path file JSON

#### OpenAI API
1. Daftar di [openai.com](https://platform.openai.com)
2. Buat API key di Settings → API Keys
3. Set `OPENAI_API_KEY`

#### Gemini API
1. Dapatkan di [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Copy API key ke `GEMINI_API_KEY`

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

# Terminal 3: Celery Worker (untuk async tasks)
celery -A mythosnote worker -l info

# Terminal 4: Celery Beat (untuk scheduled tasks)
celery -A mythosnote beat -l info
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
│   └── celery.py            # Celery configuration
│
├── apps/
│   ├── workspace/           # Workspace management
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── serializers.py
│   │   └── urls.py
│   │
│   ├── document/            # Document handling
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── tasks.py         # Celery tasks
│   │   └── urls.py
│   │
│   ├── ai/                  # AI integration
│   │   ├── models.py
│   │   ├── providers/       # Gemini, OpenAI
│   │   ├── views.py
│   │   └── urls.py
│   │
│   └── auth/                # Authentication
│       ├── models.py
│       ├── views.py
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

### Workspace
- `GET /api/workspace/` - List workspaces
- `POST /api/workspace/` - Create workspace
- `GET /api/workspace/{id}/` - Workspace detail
- `PUT /api/workspace/{id}/` - Update workspace
- `DELETE /api/workspace/{id}/` - Delete workspace

### Document
- `GET /api/document/` - List documents
- `POST /api/document/` - Upload document
- `GET /api/document/{id}/` - Document detail
- `DELETE /api/document/{id}/` - Delete document
- `POST /api/document/{id}/extract/` - Extract text

### AI Chat
- `POST /api/ai/chat/` - Send message to AI
- `GET /api/ai/chat/history/` - Chat history
- `POST /api/ai/generate/` - Generate content

### Auth
- `POST /api/auth/login/` - User login
- `POST /api/auth/register/` - User registration
- `POST /api/auth/logout/` - User logout
- `POST /api/auth/refresh/` - Refresh token

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
- [Celery Documentation](https://docs.celeryproject.org/)
- [PostgreSQL Tutorial](https://www.postgresql.org/docs/current/tutorial.html)
- [Google Cloud Storage](https://cloud.google.com/storage/docs)
- [Gemini API](https://ai.google.dev/tutorials/get_started_web)
- [OpenAI API](https://platform.openai.com/docs)

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
