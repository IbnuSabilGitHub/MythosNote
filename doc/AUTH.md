# Panduan Lengkap Sistem Autentikasi MythosNote

Dokumentasi ini menjelaskan implementasi sistem autentikasi aplikasi MythosNote dengan detail yang mudah dipahami, dirancang untuk pemula hingga pengembang berpengalaman.

---

## 📋 Daftar Isi

1. [Pengenalan Sistem](#pengenalan-sistem)
2. [Arsitektur Database](#arsitektur-database)
3. [Alur Autentikasi](#alur-autentikasi)
4. [Komponen Utama](#komponen-utama)
5. [Alur Terperinci Setiap Fitur](#alur-terperinci-setiap-fitur)
6. [Keamanan & Rate Limiting](#keamanan--rate-limiting)
7. [Dekorator & Proteksi Rute](#dekorator--proteksi-rute)
8. [Template & UI](#template--ui)
9. [Cara Menggunakan API](#cara-menggunakan-api)
10. [Async Email via Redis/RQ (Optional)](#async-email-via-redisrq-optional)
11. [Troubleshooting](#troubleshooting)

---

## Pengenalan Sistem

### Apa Itu Sistem Autentikasi?

Sistem autentikasi adalah mekanisme untuk **memverifikasi identitas pengguna** sebelum memberikan akses ke fitur-fitur aplikasi. Di MythosNote, sistem ini menangani:

- ✅ Registrasi akun baru (Sign Up)
- ✅ Masuk dengan email/username dan password (Sign In)
- ✅ Verifikasi email untuk mengakses fitur utama
- ✅ Lupa & reset password
- ✅ Login melalui Google OAuth
- ✅ Pembatasan percobaan login (rate limiting)
- ✅ Manajemen sesi pengguna (session management)
- ✅ Pelacakan penggunaan pengguna untuk kuota AI

### Alasan Pentingnya Email Verification

Email verification memastikan:
- Pengguna menggunakan email yang **valid dan milik mereka**
- Mencegah spambot membuat akun dengan email palsu
- Memastikan pengguna dapat **menerima notifikasi penting**
- Gerbang akses untuk fitur-fitur inti aplikasi

---

## Arsitektur Database

### Model `UserProfile`

```python
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

**Penjelasan:**
- **`user`**: Relasi 1-ke-1 dengan Django's built-in `User` model
  - `OneToOneField` memastikan setiap user punya 1 profile, dan sebaliknya
  - `on_delete=CASCADE`: Jika user dihapus, profilenya otomatis terhapus juga
- **`email_verified`**: Boolean flag untuk track apakah email sudah diverifikasi
  - Default `False` saat user baru mendaftar
  - Berubah jadi `True` setelah user klik link verifikasi
- **`created_at`**: Timestamp otomatis saat profile dibuat (tidak bisa diubah)
- **`updated_at`**: Timestamp otomatis yang selalu diupdate saat ada perubahan

**Diagram Relasi:**
```mermaid
erDiagram
    DjangoUser {
        int id PK
        string username UK
        string email
        string password_hash
        bool is_active
        bool is_staff
    }
    
    UserProfile {
        int user_id PK,FK
        bool email_verified
        datetime created_at
        datetime updated_at
    }
    
    DjangoUser ||--|| UserProfile : OneToOneField
```

### Model `UserUsage`

```python
class UserUsage(models.Model):
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)
    identifier = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    date = models.DateField()
    prompt_count = models.PositiveIntegerField(default=0)
    generate_count = models.PositiveIntegerField(default=0)
    failed_login_count = models.PositiveIntegerField(default=0)
    failed_login_window_started_at = models.DateTimeField(null=True, blank=True)
    last_failed_login_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "identifier", "date"],
                name="unique_user_usage_per_identifier_day",
            ),
        ]
```

**Penjelasan:**
- **`user`**: ForeignKey opsional ke User
  - Bisa `null=True` untuk melacak guest/anonymous attempts
- **`identifier`**: Normalisasi dari email/username untuk tracking
  - Contoh: "user@email.com" → "user@email.com" (lowercase)
- **`ip_address`**: IP address pengguna saat login attempt
- **`date`**: Tanggal untuk tracking per-hari (per-day quotas)
- **`failed_login_count`**: Counter untuk percobaan login gagal
- **`failed_login_window_started_at`**: Waktu mulai rate-limit window (15 menit)
  - Jika diisi, user sedang dalam "status diblokir sementara"

**Kegunaan:**
- 📊 Melacak penggunaan AI prompt & generate per hari
- 🔒 Rate limiting untuk login attempts
- 📈 Analytics penggunaan fitur
- 🚫 Deteksi dan pencegahan brute force

**Constraint Unik:**
Memastikan hanya ada 1 record per kombinasi `(user, identifier, date)`:
- Jika `user=123`, `identifier="john"`, `date="2026-05-05"`, hanya boleh ada 1 row
- Ini mencegah duplikat data dan memudahkan aggregate queries

---

## Alur Autentikasi

### Diagram Alur Utama

```mermaid
flowchart TD
    %% Guest/Anonymous User Entry
    GUEST[GUEST/ANONYMOUS USER]
    
    %% Sign Up Path
    GUEST --> SIGNUP[SIGN UP]
    SIGNUP --> CREATE[Create User & UserProfile]
    CREATE --> SEND_EMAIL[Send Verification Email]
    SEND_EMAIL --> UNVERIFIED_STATE[EMAIL UNVERIFIED<br/>awaiting verification]
    
    %% Sign In Path
    GUEST --> SIGNIN[SIGN IN]
    SIGNIN --> VERIFY_PWD[Verify Password]
    VERIFY_PWD --> CHECK_EMAIL{Check Email<br/>Verification}
    CHECK_EMAIL -->|YES| HOME[HOME/AUTHENTICATED]
    CHECK_EMAIL -->|NO| UNVERIFIED_STATE
    
    %% Google OAuth Path
    GUEST --> GOOGLE[GOOGLE OAUTH SIGN IN<br/>via token]
    GOOGLE --> GOOGLE_PROCESS[Verifikasi Google token,<br/>buat/cari user, login]
    GOOGLE_PROCESS --> GOOGLE_VERIFY[Google mark<br/>email_verified = True]
    GOOGLE_VERIFY --> HOME
    
    %% Forgot Password Path
    GUEST --> FORGOT[FORGOT PASSWORD]
    FORGOT --> SEND_RESET[Send Reset Token Email]
    SEND_RESET --> CLICK_LINK[User klik link]
    CLICK_LINK --> RESET_PAGE[RESET PASSWORD PAGE]
    RESET_PAGE --> SIGNIN_SUCCESS[SIGN IN success]
    SIGNIN_SUCCESS --> HOME
    
    %% Email Unverified Path (logged in user)
    UNVERIFIED_STATE --> RESEND_EMAIL[Resend Verification Email<br/>user logged in]
    RESEND_EMAIL --> USER_VERIFY[User verifikasi]
    USER_VERIFY --> HOME
    
    %% Styling
    style GUEST fill:#f9f,stroke:#333,stroke-width:2px
    style HOME fill:#9f9,stroke:#333,stroke-width:2px
    style UNVERIFIED_STATE fill:#ff9,stroke:#333,stroke-width:2px
    style GOOGLE fill:#bbf,stroke:#333,stroke-width:2px
```

---

## Komponen Utama

### 1. **accounts/models.py** - Database Models

**File:** [accounts/models.py](../accounts/models.py)

```python
# UserProfile: Profil kecil terpisah dari User Django
user.profile.email_verified  # Check verification status

# UserUsage: Tracking penggunaan & rate limiting
UserUsage.objects.get_or_create(user=user, identifier="john", date=today)
```

---

### 2. **accounts/views.py** - View Functions (Controllers)

**File:** [accounts/views.py](../accounts/views.py)

Setiap function menangani satu endpoint:

| Function | URL | Method | Deskripsi |
|----------|-----|--------|-----------|
| `sign_in()` | `/signin/` | GET, POST | Login dengan email/username & password |
| `sign_up()` | `/signup/` | GET, POST | Registrasi akun baru |
| `google_sign_in()` | `/auth/google/` | POST | Login via Google OAuth |
| `email_unverified()` | `/email-unverified/` | GET | Halaman verifikasi email (gerbang) |
| `resend_verification()` | `/resend-verification/` | POST | Kirim ulang email verifikasi |
| `verify_email()` | `/verify-email/<uid>/<token>/` | GET | Endpoint verifikasi dari email link |
| `forgot_password()` | `/forgot-password/` | GET, POST | Minta reset password |
| `password_reset_confirm()` | `/reset/<uid>/<token>/` | GET, POST | Confirm & set password baru |
| `sign_out()` | `/logout/` | POST | Logout & destroy session |

---

### 3. **accounts/decorators.py** - Permission Guards

**File:** [accounts/decorators.py](../accounts/decorators.py)

Dekorator adalah "penjaga" di pintu setiap view:

#### `@guest_required`
```python
@guest_required
def sign_in(request):
    # Hanya user yang belum login bisa akses
    # Jika sudah login, redirect ke 'home'
```

**Logika:**
1. User cek apakah `request.user.is_authenticated`?
2. Jika YES → redirect ke `home` (Anda sudah login, tidak perlu sign in lagi)
3. Jika NO → lanjut ke view function

**Digunakan di:** `sign_in()`, `sign_up()`, `forgot_password()`, `password_reset_confirm()`

#### `@verified_email_required`
```python
@verified_email_required
def dashboard(request):
    # Hanya user dengan email verified bisa akses
```

**Logika:**
1. User cek apakah `request.user.is_authenticated`?
   - Jika NO → redirect ke login page
2. User cek apakah `is_email_verified(user)`?
   - Jika YES → lanjut ke view function
   - Jika NO → redirect ke `email_unverified` (gerbang verifikasi)

**Digunakan di:** Fitur-fitur core (workspace, AI features, dll) - akan ditambah kemudian

---

### 3.5. **accounts/backends.py** - Custom Auth Backend (NEW v1.1.0)

**File:** [accounts/backends.py](../accounts/backends.py)

```python
class EmailBackend(ModelBackend):
    """Authenticate using email/password only (tidak username)."""
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        email = (kwargs.get("email") or username or "").strip().lower()
        if not email or not password:
            return None
        
        user = UserModel.objects.filter(email__iexact=email, is_active=True).first()
        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
```

**Purpose:** Menggantikan default ModelBackend untuk support email-only authentication.

**Perubahan v1.1.0:**
- Signup form tidak lagi ada username field
- User.username bisa `null=True` di database
- AuthenticationBackend khusus untuk email-only login

**Registrasi di settings.py:**
```python
AUTHENTICATION_BACKENDS = [
    'accounts.backends.EmailBackend',
    'django.contrib.auth.backends.ModelBackend',  # fallback
]
```

**Usage di view:**
```python
user = authenticate(request, email="john@example.com", password="password123")
# Backend akan cari user dengan email, bukan username
```

---

### 4. **accounts/forms.py** - Form Validation

**File:** [accounts/forms.py](../accounts/forms.py)

Form adalah layer validasi data sebelum masuk database:

#### `SignInForm` (Update v1.1.0)

```python
class SignInForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(strip=False, widget=forms.PasswordInput)
```

**Validasi khusus (v1.1.0):**
- ⚠️ Email ONLY (tidak ada username), beda dari versi lama
- Email divalidasi dengan `EmailField()` (format check)
- Password tidak di-strip (preserve whitespace)
- Custom `clean()` method:
  1. Check apakah ada user dengan `is_active=False` & email cocok & password benar:
     - Jika YES → set `self.inactive_user = user` (untuk auto-resend verif email di view)
     - Raise ValidationError: "Akun belum aktif. Verifikasi email dulu."
  2. Call `authenticate(request, email=email, password=password)`:
     - Backend: `EmailBackend` (custom, lihat accounts/backends.py)
     - Check: `User.objects.filter(email__iexact=email, is_active=True)`
     - Verify password: `user.check_password(password)`
  3. Jika `authenticate()` return None → raise ValidationError: "Email atau password salah."
- Error message: "Email atau password salah."

**Perbedaan v1.0 → v1.1.0:**
```
v1.0:
  username_or_email = forms.CharField()
  # Support both email & username
  
v1.1.0:
  email = forms.EmailField()
  # Email ONLY, username dihapus sepenuhnya
```

#### `SignUpForm` (Update v1.1.4)

```python
class SignUpForm(forms.ModelForm):
    password = forms.CharField(strip=False, widget=forms.PasswordInput)
    password_confirm = forms.CharField(strip=False, widget=forms.PasswordInput)
    
    class Meta:
        model = User
        fields = ["email"]
```

**Validasi khusus (v1.1.2, v1.1.4):**
- **Email field** (NEW: validate_real_email):
  - Format check via `EmailField()`
  - Domain check: Validate domain exists + MX record valid
  - Function: `validate_real_email(email)` dari [accounts/validators.py](../accounts/validators.py)
  - Library: `email-validator` package (diperlukan di requirements.txt)
  - Error: "Email atau domain email tidak valid." (jika domain invalid)
  - Case-insensitive unique check: "Email sudah terdaftar."
  
- **Password fields:**
  - `strip=False`: Preserve whitespace (jangan auto-trim)
  - Confirm match: `password == password_confirm`
    - Error jika tidak cocok: "Password tidak cocok."
  - Django password strength validation:
    - Min length: 8 characters
    - Not all numeric
    - Not too similar dengan username/email
    - Not in common password list
  
- **Save method:**
  - user.email = validated & normalized email
  - user.username = None (v1.1.0 change)
  - user.set_password() → hash password
  - user.save()
  - Auto-signal: UserProfile created dengan email_verified=False

**Perbedaan v1.0 → v1.1.0 → v1.1.2 → v1.1.4:**
```
v1.0:
  username = forms.CharField()
  email = forms.EmailField()
  # Support both username & email for signup
  
v1.1.0:
  email = forms.EmailField()  # username dihapus
  
v1.1.2:
  email = forms.EmailField()  # + validate_real_email() (domain check)
  
v1.1.4:
  email = forms.EmailField()  # same, tapi user sekarang inactive by default
```

#### `ForgotPasswordForm`

```python
class ForgotPasswordForm(forms.Form):
    email = forms.EmailField()
```

Simple email-only form (tidak reveal apakah email terdaftar atau tidak).

#### `PasswordResetConfirmForm`

```python
class PasswordResetConfirmForm(SetPasswordForm):
    """Inherit dari Django's SetPasswordForm"""
    
    def clean_new_password1(self):
        """Tolak password baru yang sama dengan password lama"""
        password = self.cleaned_data.get("new_password1", "")
        if password and self.user.check_password(password):
            raise ValidationError("Password baru tidak boleh sama dengan password lama.")
        return password
```

- Inherit dari Django's built-in `SetPasswordForm`
- Extra validation: Prevent user set password yang sama dengan password lama

---

### 5. **accounts/validators.py** - Email Validation (NEW v1.1.2)

**File:** [accounts/validators.py](../accounts/validators.py)

```python
def validate_real_email(email: str) -> str:
    """Validasi format email + domain + MX. Return email normalisasi."""
    try:
        result = validate_email(email, check_deliverability=True)
        return result.normalized
    except EmailNotValidError as exc:
        raise ValidationError(ERROR_INVALID_EMAIL) from exc
```

**Library:** `email-validator` (package eksternal, tambah ke requirements.txt)

**Checks:**
- Format: RFC 5321 compliance
- Domain exists: DNS lookup
- MX records: Domain punya mail server yang valid
- Deliverability: Praktis bisa terima email

**Usage:**
```python
# Di SignUpForm.clean_email():
email = validate_real_email(self.cleaned_data["email"])
```

**Error:**
- "Email atau domain email tidak valid." (user-friendly message)

---

### 6. **accounts/utils.py** - Helper Functions

**File:** [accounts/utils.py](../accounts/utils.py)

Utility functions yang dipakai di views & decorators:

#### Rate Limiting Functions
```python
get_login_usage(request, identifier)
# Fetch/create today's usage record

is_login_rate_limited(usage)
# Check jika user sudah exceed 5 attempts dalam 15 menit

record_failed_login(usage)
# Increment failed_login_count & set window timer

clear_failed_login_tracking(usage)
# Reset counters setelah login success
```

**Contoh alur:**
```
1. User input username & password SALAH
   → record_failed_login(usage)
   → failed_login_count = 1

2. User coba lagi, SALAH lagi
   → record_failed_login(usage)
   → failed_login_count = 2

3. ... (3 kali lagi = total 5 kali)

4. User coba ke-6 kali
   → is_login_rate_limited(usage) = True
   → Block dengan pesan: "Terlalu banyak percobaan login..."

5. User tunggu 15 menit, atau di menit ke-16 coba lagi
   → Window expired
   → is_login_rate_limited(usage) = False
   → Blokir dibuka, user bisa coba login lagi
```

#### Email Verification Functions
```python
is_email_verified(user)
# Get/create UserProfile & check email_verified flag

send_verification_email(request, user)
# Generate signed token URL & send via email

send_password_reset_email(request, user)
# Generate signed reset token URL & send via email
```

#### Email Token Generation
```python
uid = urlsafe_base64_encode(force_bytes(user.pk))
# Encode user ID menjadi URL-safe string
# Contoh: user.id=123 → "MTIz"

token = default_token_generator.make_token(user)
# Generate signed token (Django default)
# Contoh: "xyz-abc-def..."
# Token ini hanya valid untuk user tertentu, & expire dalam beberapa hari
```

#### Google OAuth Verification
```python
verify_google_credential(credential)
# Validate Google token via Google's tokeninfo endpoint
# Verifikasi `aud` (audience) cocok dengan GOOGLE_OAUTH_CLIENT_ID
# Return: {"email": ..., "name": ..., "email_verified": ...}
```

---

### 7. **accounts/urls.py** - URL Routing

**File:** [accounts/urls.py](../accounts/urls.py)

```python
urlpatterns = [
    path("signin/", views.sign_in, name="signin"),
    path("signup/", views.sign_up, name="signup"),
    path("auth/google/", views.google_sign_in, name="google_signin"),
    path("forgot-password/", views.forgot_password, name="forgot_password"),
    path("reset/<uidb64>/<token>/", views.password_reset_confirm),
    path("email-unverified/", views.email_unverified, name="email_unverified"),
    path("resend-verification/", views.resend_verification, name="resend_verification"),
    path("verify-email/<uidb64>/<token>/", views.verify_email, name="verify_email"),
    path("logout/", views.sign_out, name="logout"),
]
```

Semua route di-mount di `config/urls.py`:
```python
urlpatterns = [
    path('', views.home, name='home'),
    path('', include('accounts.urls')),  # ← Include accounts URLs di root
]
```

Jadi URL final:
- `/signin/` (bukan `/accounts/signin/`)
- `/signup/`
- `/verify-email/MTIz/xyz-token/`
- dll

---

### 8. **accounts/context_processors.py** - Template Context

**File:** [accounts/context_processors.py](../accounts/context_processors.py)

Context processor adalah function yang "inject" data ke semua templates secara otomatis:

```python
def auth_settings(request):
    email_verified = False
    if request.user.is_authenticated:
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        email_verified = profile.email_verified

    return {
        "GOOGLE_OAUTH_CLIENT_ID": settings.GOOGLE_OAUTH_CLIENT_ID,
        "AUTH_EMAIL_VERIFIED": email_verified,
    }
```

**Hasil:** Di semua template, bisa akses:
```html
{{ GOOGLE_OAUTH_CLIENT_ID }}  <!-- Public Google Client ID -->
{{ AUTH_EMAIL_VERIFIED }}     <!-- True jika email sudah verified -->
```

Register di `settings.py`:
```python
'OPTIONS': {
    'context_processors': [
        ...
        'accounts.context_processors.auth_settings',  # ← Added
    ],
},
```

---

## Alur Terperinci Setiap Fitur

### Fitur 1: Sign Up (Registrasi)

**URL:** `POST /signup/`

**⚠️ PENTING:** User dibuat dalam status **INACTIVE** dan TIDAK auto-login. Email harus diverifikasi terlebih dahulu.

**Step-by-step:**

```
1. User akses GET /signup/
   → Render signup.html dengan form kosong
   → Form field: email, password, password_confirm (TIDAK ada username)
   
2. User input:
   - email: "john@example.com"
   - password: "SecurePass123!"
   - password_confirm: "SecurePass123!"
   
3. User submit POST /signup/
   → View sign_up() dipanggil
   
4. Validasi form (SignUpForm):
   a) Email valid format? → validate_real_email() cek format + domain + MX
      - Jika invalid → error: "Email atau domain email tidak valid."
   b) Email sudah terdaftar (case-insensitive)? → error: "Email sudah terdaftar."
   c) Password & confirm match? YES → OK
   d) Password strength OK? (Django default checks)
   
5. Form valid:
   → Create Django User:
      - username: None (nullable, tidak unique lagi)
      - email: "john@example.com"
      - password: (hashed via set_password())
      - is_active: False ← INACTIVE! (CHANGE from v1.1.4)
      - is_staff: False
      - is_superuser: False
   
   → Signal triggered (django.db.models.post_save):
      - Auto-create UserProfile untuk user baru
      - profile.email_verified = False
      - profile.created_at = now()
   
   → send_verification_email(request, user):
      - Generate uid = urlsafe_base64_encode(user.pk)
      - Generate token = email_verification_token_generator.make_token(user)
        (Token this tied to user.pk, user.password, user.email, & profile.email_verified)
      - Build URL: /verify-email/MTIz/xyz-token/
      - Update profile.last_verification_email_sent_at = now()
      - Send email dengan subject "Verifikasi email MythosNote"
   
   → messages.success(...): "Akun berhasil dibuat. Cek email, lalu login setelah verifikasi."
   
   → redirect("signin"):
      - Redirect ke halaman login
      - User HARUS login lagi setelah verifikasi email
      
6. User cek email inbox
   → Klik link verifikasi
   → GET /verify-email/MTIz/xyz-token/
   
7. Verify endpoint:
   a) Decode uid → user.id = 123
   b) Get user dari database
   c) Check token dengan email_verification_token_generator.check_token(user, token)
      - Token ini signed dengan user password & email_verified status
      - Jika email_verified sudah berubah, token invalid
      - Token valid hanya untuk user tertentu
   d) Jika valid:
      - Set user.is_active = True
      - Set user.profile.email_verified = True
      - if request.user.is_authenticated: logout(request) ← logout user sebelumnya jika ada
      - messages.success(...): "Email berhasil diverifikasi. Silakan login."
      - redirect("signin")
   e) Jika invalid/expired:
      - messages.error(...): "Link verifikasi tidak valid atau sudah kedaluwarsa."
      - render("auth/email_verification_invalid.html")
      - User bisa lihat link untuk "resend verification email"
      
8. User login lagi dengan email
   → POST /signin/
   → (lihat Fitur 2)
```

**Database state sesudah signup:**

| Table | Data |
|-------|------|
| auth_user | id=1, username=None, email="john@example.com", password_hash="...", is_active=0 |
| accounts_userprofile | id=1, user_id=1, email_verified=0, last_verification_email_sent_at="2026-05-05 10:00:00", created_at="2026-05-05 10:00:00" |
| accounts_userusage | user_id=None, identifier="john@example.com", date="2026-05-05", ... |

**Email yang dikirim:**

```
To: john@example.com
Subject: Verifikasi email MythosNote

Halo,

Klik link berikut untuk memverifikasi email MythosNote Anda:
http://localhost:8000/verify-email/MTIz/xyz-abc-def-token/

Jika Anda tidak membuat akun MythosNote, abaikan email ini.
```

**Validasi Email Baru (v1.1.2):**
- Library: `email-validator`
- Check: Format valid + Domain exists + MX record valid
- Error message: "Email atau domain email tidak valid."
- Function: `validate_real_email(email)` di [accounts/validators.py](../accounts/validators.py)


---

### Fitur 2: Sign In (Login)

**URL:** `POST /signin/`

**⚠️ PERUBAHAN v1.1.0:** Login sekarang **email-only**, bukan username/email. Field username di form dihapus.

**Step-by-step:**

```
1. User akses GET /signin/
   → @guest_required check:
      - Sudah login? NO → OK lanjut
      - Sudah login? YES → redirect("home")
   → Render signin.html dengan form kosong
   → Form field: email, password (TIDAK ada username)
   
2. User input:
   - email: "john@example.com"
   - password: "SecurePass123!"
   
3. User submit POST /signin/
   → View sign_in() dipanggil
   
4. Cek rate limiting:
   a) get_login_usage(request, email)
      → UserUsage record untuk hari ini (atau create baru)
      → Normalize identifier: email.strip().lower()
   b) is_login_rate_limited(usage)?
      - Jika yes (5+ attempts dalam 15 min) → error message & re-render form
      - Jika no → lanjut
   
5. Validasi form (SignInForm):
   a) Clean method:
      - Check apakah ada user dengan is_active=False & email cocok & password benar
        - YES → set self.inactive_user = user ← untuk auto-resend verif email
        - Then raise ValidationError: "Akun belum aktif. Verifikasi email dulu."
      - authenticate(request, email=email, password=password)
        - EmailBackend backend: filter is_active=True & email iexact & password match
        - Return user jika valid, else None
      - Jika self.user is None → raise ValidationError: "Email atau password salah."
   
6. Form valid & password benar & user active:
   a) login(request, user):
      - Create Django session
      - request.user sekarang authenticated
   
   b) clear_failed_login_tracking(usage):
      - Set failed_login_count = 0
      - Set failed_login_window_started_at = None
      - Set last_failed_login_at = None
   
   c) is_email_verified(user)?
      - YES → redirect("home")
      - NO → redirect("email_unverified") ← gerbang verifikasi
   
7. Form invalid - user inactive tapi password benar:
   (Dari CHECK #5a di atas)
   
   a) Check can_send_verification_email(form.inactive_user)?
      - Check: now() - last_verification_email_sent_at >= 5 menit
      - YES → send_verification_email(request, form.inactive_user)
      - messages.error: "Akun belum aktif. Link verifikasi baru sudah dikirim."
      - Automatic resend! ← (NEW in v1.1.4)
   
   b) Jika cooldown belum lewat:
      - get_verification_resend_wait_seconds(user) → e.g., 120 seconds
      - messages.error: "Akun belum aktif. Cek email verifikasi Anda atau tunggu 120 detik untuk kirim ulang."
   
   c) Re-render form dengan error
   
8. Form invalid - password salah atau user tidak ditemukan:
   a) record_failed_login(usage):
      - Jika belum ada window, set failed_login_window_started_at = now()
      - Increment failed_login_count
      - Set last_failed_login_at = now()
   
   b) Jika failed_login_count >= 5:
      - BLOCKED sampai 15 menit lewat
   
   c) messages.error(...): "Email atau password salah."
   
   d) Re-render form dengan error (keep email field filled)
```

**Database state:**

| Table | Data |
|-------|------|
| django_session | session_key="...", session_data="...", expire_date="2026-05-19" |
| accounts_userusage | ..., failed_login_count=0 atau > 0, failed_login_window_started_at="2026-05-05 10:05:00" |

**Custom Auth Backend (v1.1.0):**
- File: [accounts/backends.py](../accounts/backends.py)
- Class: `EmailBackend` (inherit dari ModelBackend)
- Authenticate method: Accept `email` kwarg, filter `email__iexact` & `is_active=True`
- Usage: Di settings.py `AUTHENTICATION_BACKENDS` sudah include EmailBackend

---

### Fitur 3: Email Verification Gate

**URL:** `GET /email-unverified/`

**Peraturan:**
- Hanya user yang sudah login (`@login_required`)
- Hanya user dengan `email_verified=False` bisa lihat halaman ini
- Jika email sudah verified, redirect ke home

**Step-by-step:**

```
1. User (logged in, unverified) akses GET /email-unverified/
   → Decorator check:
      - @login_required: is_authenticated? YES → OK
      - if is_email_verified(user)? NO → lanjut
   
   → Render auth/email_unverified.html
   
2. Template tampilkan:
   - Pesan: "Email belum terverifikasi. Cek inbox untuk link verifikasi..."
   - Tombol 1: "Kirim Ulang Link"
   - Tombol 2: "Logout / Ganti Akun"
   
3. User click "Kirim Ulang Link"
   → POST /resend-verification/
   → View resend_verification():
      a) Check is_email_verified? NO → OK lanjut
      b) send_verification_email(request, user)
      c) messages.success(...): "Link verifikasi baru sudah dikirim."
      d) redirect("email_unverified")
      
4. User click "Logout / Ganti Akun"
   → POST /logout/
   → View sign_out():
      a) logout(request): Destroy session
      b) redirect("home")
```

**Tujuan fitur ini:**
- Memaksa user memverifikasi email sebelum akses workspace
- Pastikan email valid (pengguna bisa receive notifications)
- Gerbang yang mudah dipahami

---

### Fitur 3.5: Resend Verification Email dengan Cooldown (v1.1.2 & v1.1.4)

**URL:** `POST /resend-verification/`

**⚠️ NEW:** Ada cooldown **5 menit** antar pengiriman verification email (prevent spam).

**Step-by-step:**

```
1. User login tapi email belum verified → di halaman /email-unverified/
   → Tombol "Kirim Ulang Link" ada
   
2. User klik tombol
   → POST /resend-verification/
   
3. View resend_verification():
   a) Check is_email_verified(request.user)? YES → redirect("home")
   
   b) Check can_send_verification_email(request.user)?
      - Function cek: now() - profile.last_verification_email_sent_at >= 5 menit
      - Jika YES (boleh kirim) → lanjut
      - Jika NO (terlalu cepat) → error & redirect
   
   c) Jika boleh kirim:
      - send_verification_email(request, request.user)
      - Update profile.last_verification_email_sent_at = now()
      - messages.success(...): "Link verifikasi baru sudah dikirim."
      - redirect("email_unverified")
   
   d) Jika terlalu cepat (cooldown aktif):
      - get_verification_resend_wait_seconds(request.user) → e.g., 120 seconds
      - messages.warning(...): f"Tunggu 120 detik sebelum kirim ulang."
      - redirect("email_unverified")
```

**Frontend Countdown Timer:**
```html
<!-- Template: auth/email_unverified.html -->
<button id="resend-btn" type="submit">Kirim Ulang Link</button>
<span id="cooldown-timer" style="display: none;">
    Tunggu <span id="seconds">120</span> detik...
</span>

<script>
// Auto-disable button jika cooldown masih aktif
const waitSeconds = {{ resend_wait_seconds }};  // From view context
if (waitSeconds > 0) {
    document.getElementById('resend-btn').disabled = true;
    document.getElementById('cooldown-timer').style.display = 'inline';
    
    let remaining = waitSeconds;
    const timerInterval = setInterval(() => {
        remaining--;
        document.getElementById('seconds').textContent = remaining;
        if (remaining <= 0) {
            clearInterval(timerInterval);
            document.getElementById('resend-btn').disabled = false;
            document.getElementById('cooldown-timer').style.display = 'none';
        }
    }, 1000);
}
</script>
```

**Database state:**
```python
profile.last_verification_email_sent_at = "2026-05-05 14:00:00"

# User coba resend di 14:03
# get_verification_resend_wait_seconds() → 120 seconds (cooldown masih aktif)

# User coba resend di 14:05
# get_verification_resend_wait_seconds() → 0 (boleh kirim!)
```

**Email Token Invalidation (v1.1.2):**
```python
# Token generator: EmailVerificationTokenGenerator (custom)
# Token di-hash dengan:
# - user.pk
# - user.password
# - timestamp
# - profile.email_verified ← PENTING!
# - profile.last_verification_email_sent_at ← PENTING!
# - user.email

# Akibat: Jika user kirim ulang email (update last_verification_email_sent_at),
# token lama menjadi INVALID otomatis!

# Ini prevent:
# - User kopinya lama token masih berlaku
# - Token lama bisa dipakai berkali-kali
```

---

### Fitur 4: Email Verification via Link (Update v1.1.4)

**URL:** `GET /verify-email/<uidb64>/<token>/`

**⚠️ PERUBAHAN v1.1.4:** 
- User dibuat dengan `is_active=False`, verification link mengaktifkan user sekaligus marking email_verified
- If user sudah login, auto-logout saat verifikasi berhasil (security: biar user login ulang dari email yang sudah verified)

**Step-by-step:**

```
1. User klik link dari email:
   http://localhost:8000/verify-email/MTIz/xyz-abc-def-token/
   
   → GET /verify-email/MTIz/xyz-abc-def-token/
   
2. View verify_email(request, uidb64, token):
   
   a) get_user_from_uid("MTIz"):
      - Decode: urlsafe_base64_decode("MTIz") → b"123"
      - force_str() → "123"
      - Query: User.objects.get(pk=123)
      - Return user object atau None
   
   b) Check token:
      - email_verification_token_generator.check_token(user, token)
      - Token ini signed dengan:
        * user.pk
        * user.password
        * timestamp
        * profile.email_verified
        * profile.last_verification_email_sent_at
        * user.email
      - Jika user ubah password, atau admin edit email_verified, token invalid
      - Jika user resend email (update last_verification_email_sent_at), token lama invalid
      - Token expire dalam beberapa hari (Django default: 1 hari)
   
   c) Jika valid:
      - Set user.is_active = True ← ACTIVATE user (NEW in v1.1.4)
      - Set user.profile.email_verified = True
      - user.profile.save(update_fields=["email_verified", "updated_at"])
      
      - if request.user.is_authenticated:
          logout(request) ← Auto-logout user sebelumnya! (NEW in v1.1.4)
          # This ensure user login ulang dari email yang sudah verified
      
      - messages.success(...): "Email berhasil diverifikasi. Silakan login."
      - redirect("signin")
   
   d) Jika invalid/expired:
      - messages.error(...): "Link verifikasi tidak valid atau sudah kedaluwarsa."
      - render("auth/email_verification_invalid.html")
      - User bisa lihat link untuk "resend verification email" atau kembali ke signin
      
3. User login dengan credential di /signin/
   → (lihat Fitur 2)
```

**Contoh Scenario:**

```
Scenario 1: Fresh signup user
1. User signup, is_active=False, email_verified=False
2. User terima email dengan link verifikasi
3. User klik link → is_active=True, email_verified=True
4. User redirect ke signin → login dengan email & password

Scenario 2: User ubah password di tengah proses
1. User signup, terima email dengan link verifikasi
2. User (belum verify) reset password via forgot_password
3. User terima email reset password, ubah password
4. Sekarang link verifikasi LAMA menjadi INVALID (karena user.password berubah)
5. User harus resend email verifikasi baru atau login & resend ulang

Scenario 3: User resend verification email
1. User signup, terima email verifikasi pertama (token A)
2. User tidak klik link, request resend
3. profile.last_verification_email_sent_at updated
4. Token A sekarang INVALID (karena last_verification_email_sent_at berubah)
5. User terima email baru dengan token B (yang valid)
```

---

### Fitur 5: Forgot Password

**URL:** `GET,POST /forgot-password/`

**Step-by-step:**

```
1. User lupa password, akses GET /forgot-password/
   → @guest_required: Sudah login? NO → OK lanjut
   → Render forgot_password.html dengan form kosong
   
2. User input email: "john@example.com"
   → POST /forgot-password/
   
3. View forgot_password():
   a) Validasi email format
   b) Query User.objects.filter(email__iexact="john@example.com", is_active=True)
      - Bisa ada multiple users dengan email sama? NO (email field ada constraint)
      - Jika tidak ada user → loop tidak jalan, tidak ada email dikirim
   
   c) For each user dengan email tersebut:
      - send_password_reset_email(request, user):
        a) Generate uid = urlsafe_base64_encode(user.pk)
        b) Generate token = default_token_generator.make_token(user)
        c) Build URL: /reset/MTIz/xyz-token/
        d) Kirim email dengan link ini
   
   d) messages.success(...): 
      "Jika email terdaftar, link reset password akan dikirim."
      (Pesan generic, tidak reveal apakah email terdaftar atau tidak)
   
   e) redirect("signin")
   
4. User check email inbox
   → Klik link reset password
   → GET /reset/MTIz/xyz-token/
```

**Alasan generic message:**
- Keamanan! Jangan reveal apakah email terdaftar atau tidak
- Prevent attackers dari enumerate valid emails

---

### Fitur 6: Password Reset Confirm

**URL:** `GET,POST /reset/<uidb64>/<token>/`

**Step-by-step:**

```
1. User klik link dari email:
   http://localhost:8000/reset/MTIz/xyz-token/
   
   → GET /reset/MTIz/xyz-token/
   
2. View password_reset_confirm():
   
   a) get_user_from_uid("MTIz")
      - Decode uid → user object
   
   b) default_token_generator.check_token(user, "xyz-token")
      - Token valid & belum expired? YES → lanjut
      - Token invalid/expired? NO → render error page
   
   c) Jika token valid:
      - Render password_reset_confirm.html dengan PasswordResetConfirmForm
      - Form ada 2 field: new_password1, new_password2
      - User input & submit
   
   d) POST /reset/MTIz/xyz-token/:
      - PasswordResetConfirmForm.save():
        a) Validasi password cocok & strength OK
        b) Set user.password = hashed_password
        c) user.save()
      - messages.success(...): "Password berhasil direset. Silakan login."
      - redirect("signin")
   
   e) Jika token invalid/expired:
      - render("auth/password_reset_invalid.html")
      - User bisa klik link di halaman untuk kembali ke forgot password
      
3. User login dengan password baru
   → POST /signin/ dengan password baru
```

---

### Fitur 7: Google OAuth Sign In (Update v1.1.0 & v1.1.1)

**URL:** `POST /auth/google/`

**⚠️ PERUBAHAN v1.1.0 & v1.1.1:**
- Username dihapus dari signup form, hanya email
- Google OAuth membuat user dengan `username=None`
- User dibuat dengan `password=unusable` (bukan empty string)
- Email dari Google OAuth otomatis marked as `email_verified=True` jika payload `email_verified=True`
- Rate limiting: Max 10 attempts per IP dalam 300 detik (5 menit)

**Prerequisite:**
- Setup Google OAuth di Google Cloud Console
- Config `GOOGLE_OAUTH_CLIENT_ID` di `settings.py`
- Tambahkan authorized origins di GCP: `http://localhost:8000`, `http://wsl.localhost:8000`, `http://localhost:5173`
- Tambahkan `SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin-allow-popups'` pada `settings.py` 
  - Mencegah masalah popup token nyangkut/stuck di GSI redirect pada Django 4.0+
- Frontend load Google Identity Services library & handle token generation

**Step-by-step:**

```
1. Frontend (JavaScript):
   a) User klik "Login with Google"
   b) Google Identity Services modal dimunculkan
   c) User confirm dengan Google account
   d) Google return ID token (JWT)
   e) JavaScript POST token ke /auth/google/
   
2. Backend POST /auth/google/:
   a) Check is_google_oauth_rate_limited(request)?
      - Cache key: "google-oauth-rate:{ip_address}"
      - Limit: 10 attempts per 300 detik (5 menit)
      - Jika terlampaui → error: "Terlalu banyak percobaan Google login. Coba lagi nanti."
   
   b) View google_sign_in():
      - Get credential dari POST data
      - Jika kosong → error: "Credential Google tidak ditemukan."
   
   c) verify_google_credential(credential):
      - HTTP GET ke https://oauth2.googleapis.com/tokeninfo?id_token=...
      - Timeout: 8 detik
      - Check apakah `aud` (audience) == GOOGLE_OAUTH_CLIENT_ID
        - Jika tidak cocok → ValueError("Token Google tidak sesuai client aplikasi.")
      - Check apakah ada field `email` → Jika tidak → ValueError("Token Google tidak berisi email.")
      - Extract: 
        * email: payload["email"].lower() (normalized)
        * name: payload.get("name", "")
        * email_verified: payload.get("email_verified") in (True, "true", "True")
      - Return: {"email": ..., "name": ..., "email_verified": ...}
   
   d) get_or_create_google_user(payload):
      - Use atomic transaction untuk thread-safety
      - Query User.objects.filter(email__iexact=payload["email"])
      - Jika ada (existing user):
        → gunakan existing user
        → update profile.email_verified jika payload["email_verified"]=True
      - Jika tidak ada (new user):
        → Create new User:
           * username: None (nullable di database sejak v1.1.0)
           * email: payload["email"]
           * password: set_unusable_password() ← TIDAK ada password!
           * is_active: True (beda dari signup yang is_active=False)
        → Signal auto-create UserProfile
        → If payload["email_verified"]=True:
           * profile.email_verified = True (no need to verify!)
      
   e) login(request, user, backend="django.contrib.auth.backends.ModelBackend"):
      - Create Django session
      - Explicit backend specification (best practice)
   
   f) is_email_verified(user)?
      - YES (Google already verified) → redirect("home")
      - NO (rare case) → redirect("email_unverified") ← user bisa resend
      
3. Keuntungan Google OAuth:
   - Email sudah diverifikasi oleh Google server
   - Tidak perlu password verification
   - Faster signup & login
   - Lebih aman (Google handle auth complexity)
```

**Error handling:**
```
- Rate limited → "Terlalu banyak percobaan Google login. Coba lagi nanti."
- Credential not found → "Credential Google tidak ditemukan."
- Token validation fail → "Login Google gagal divalidasi."
- Audience mismatch → (user dapat generic error di view)
- Email not in token → (user dapat generic error di view)
- Email already linked to other account (IntegrityError) 
  → "Email Google sudah terhubung ke akun lain."
```

**Database state (Google OAuth user):**

```
auth_user:
  id=2, username=None, email="john@gmail.com", password="!", is_active=1

accounts_userprofile:
  user_id=2, email_verified=1, created_at="2026-05-05 14:30:00"

accounts_userusage:
  user_id=2, identifier="john@gmail.com", date="2026-05-05"
```

**Email Verification Token for Google Users:**
- User dari Google OAuth TIDAK perlu verifikasi email ulang
- Token generator hanya dipakai jika email_verified=False

---

### Fitur 8: Logout

**URL:** `POST /logout/`

**Step-by-step:**

```
1. User submit form dengan action="/logout/"
   → POST /logout/
   
2. View sign_out():
   a) logout(request):
      - Delete session key dari server
      - Clear cookies di client
      - request.user menjadi AnonymousUser
   
   b) messages.success(...): "Anda sudah logout."
   
   c) redirect("home"):
      - User kembali ke halaman utama
      - request.user.is_authenticated = False
      
3. Navigation bar update:
   - Hide "Verify Email" link (jika ada)
   - Hide "Logout" button
   - Show "Sign In" link
   - Show "Get Started" button
```

---

## Fitur Maintenance: Cleanup Unverified Users (v1.1.5)

**Command:** `python manage.py cleanup_unverified_users`

**Tujuan:** Otomatis menghapus akun yang never verified dalam jangka waktu tertentu (default 24 jam).

**Opsi:**
```bash
# Preview (dry-run):
python manage.py cleanup_unverified_users --dry-run

# Hapus dengan konfirmasi:
python manage.py cleanup_unverified_users

# Hapus tanpa konfirmasi:
python manage.py cleanup_unverified_users --no-confirm

# Custom cutoff (72 jam):
python manage.py cleanup_unverified_users --days 72

# Custom batch size:
python manage.py cleanup_unverified_users --batch-size 50
```

**Kriteria Penghapusan:**
```python
User.objects.filter(
    is_active=False,                    # User belum pernah aktif
    profile__email_verified=False,      # Email belum pernah diverifikasi
    date_joined__lte=cutoff_date        # Terdaftar lebih dari X hari lalu
)
```

**Contoh timeline:**
```
2026-05-05 10:00:00 - User signup, is_active=False
2026-05-05 10:01:00 - Verification email dikirim
2026-05-05 14:00:00 - User tidak verifikasi, masih inactive

2026-05-06 10:00:00 (24 jam kemudian) - Command dijalankan:
  - Jika --days 1 (default)
  - Cutoff = 2026-05-05 10:00:00
  - User akan DIHAPUS!
  
2026-05-06 09:59:00 (< 24 jam) - Command dijalankan:
  - Cutoff = 2026-05-05 10:00:01
  - User masih ada (belum 24 jam lewat)
```

**Use Cases:**
- Scheduled via cron job setiap malam
- Manual cleanup setelah campaign/spam signup
- Maintenance task di production (safe: hanya inactive & unverified users)

**Safety Features:**
- `--dry-run`: Preview tanpa menghapus
- `--no-confirm`: Skip prompt (untuk automation)
- Batch processing: Process 100 per batch (configurable)
- Logging lengkap: Siapa dihapus, kapan, berapa banyak
- Idempotent: Aman dijalankan berkali-kali


## Keamanan & Rate Limiting

### 1. Password Hashing

```python
# Django AUTOMATICALLY hash password:
user.set_password("plaintext_password")
# Database store: pbkdf2_sha256$xyz$...

# Verify:
authenticate(username="john", password="plaintext_password")
# Django auto-compare dengan hash di database
```

**Benefit:**
- Bahkan admin tidak bisa lihat password original
- Jika database compromise, password masih aman

### 2. Rate Limiting pada Login

**Algoritma:**

```python
LOGIN_RATE_LIMIT_ATTEMPTS = 5          # Block setelah 5 attempt gagal
LOGIN_RATE_LIMIT_WINDOW = timedelta(minutes=15)  # Window 15 menit

def is_login_rate_limited(usage):
    # Jika failed_login_count >= 5 dan window belum expired → BLOCK
    
    if not usage.failed_login_window_started_at:
        return False  # Belum ada window, OK
    
    window_expires_at = usage.failed_login_window_started_at + LOGIN_RATE_LIMIT_WINDOW
    if timezone.now() >= window_expires_at:
        # Window sudah expired, reset counter
        usage.failed_login_count = 0
        usage.failed_login_window_started_at = None
        usage.save()
        return False  # OK, bisa coba lagi
    
    # Window masih aktif, check counter
    return usage.failed_login_count >= LOGIN_RATE_LIMIT_ATTEMPTS
```

**Timeline Contoh:**

```
14:00 - Failed attempt #1 → window_started_at = 14:00, count = 1
14:01 - Failed attempt #2 → count = 2
14:02 - Failed attempt #3 → count = 3
14:03 - Failed attempt #4 → count = 4
14:04 - Failed attempt #5 → count = 5, BLOCKED
14:05 - User coba lagi → is_login_rate_limited = True → ERROR
14:15 - User coba lagi → still blocked (exactly at 15 min mark)
14:16 - User coba lagi → window expired! count reset → OK, bisa coba
```

**Tracked by:**
- `UserUsage.identifier` (normalized email/username, case-insensitive)
- `UserUsage.date` (per-day granularity)
- Per IP juga bisa (untuk guest attempts sebelum user ditemukan)

### 3. CSRF Protection

```html
<!-- Template harus include CSRF token di form -->
<form method="post" action="/signin/">
    {% csrf_token %}  <!-- Django auto-generate hidden input -->
    <input name="username" type="text" />
    <input name="password" type="password" />
</form>
```

**Middleware di settings.py:**
```python
MIDDLEWARE = [
    ...
    'django.middleware.csrf.CsrfViewMiddleware',
    ...
]
```

**Benefit:**
- Prevent cross-site form submission attacks
- Token tied ke session user

### 4. Secure Password Reset Tokens

```python
# Token generation:
token = default_token_generator.make_token(user)
# Django use: hash(user.pk + user.password + timestamp)
# Token tied ke specific user & password
# Token expire dalam 1-7 hari (configurable)

# Token validation:
valid = default_token_generator.check_token(user, token)
# Jika user ubah password, token invalid otomatis
```

**Benefit:**
- Token tidak reusable setelah password berubah
- Token expire otomatis
- Tidak ada permanent reset link

### 5. Email Verification Tokens

```python
# Sama seperti password reset tokens
uid = urlsafe_base64_encode(force_bytes(user.pk))  # Encode user ID
token = default_token_generator.make_token(user)   # Sign token

# Email link format:
# /verify-email/MTIz/xyz-token/
```

### 6. Google OAuth Audience Check

```python
payload = response.json()
if payload.get("aud") != settings.GOOGLE_OAUTH_CLIENT_ID:
    raise ValueError("Token tidak sesuai client aplikasi")

# Ini prevent:
# - Token dari Google app lain tidak bisa dipakai
# - Man-in-the-middle attacks
```

### 6.5. Google OAuth Rate Limiting (NEW v1.1.1)

**Algoritma:**

```python
GOOGLE_OAUTH_RATE_LIMIT_ATTEMPTS = 10
GOOGLE_OAUTH_RATE_LIMIT_WINDOW = 300  # 5 menit

def is_google_oauth_rate_limited(request):
    ip_address = get_client_ip(request) or "unknown"
    cache_key = f"google-oauth-rate:{ip_address}"
    attempts = cache.get(cache_key, 0)
    
    if attempts >= GOOGLE_OAUTH_RATE_LIMIT_ATTEMPTS:
        return True  # BLOCKED
    
    cache.set(cache_key, attempts + 1, GOOGLE_OAUTH_RATE_LIMIT_WINDOW)
    return False  # OK, increment & allow
```

**Tracking by:**
- IP Address (per-IP limit)
- Cache backend (Redis, Memcached, atau in-memory)
- 5-minute sliding window

**Timeline Example:**

```
14:00:00 - User attempt #1  → attempts=1, cache TTL=5 min
14:00:05 - User attempt #2  → attempts=2
...
14:00:45 - User attempt #10 → attempts=10, LIMIT REACHED
14:00:46 - User attempt #11 → is_google_oauth_rate_limited = True → BLOCKED!
14:05:01 - Cache expired, attempts reset
14:05:02 - User attempt #12 → cache cleared, attempts=1, OK!
```

**Use Case:**
- Prevent brute force Google token attacks
- Different from login rate limiting (per-email)
- Login: 5 attempts per 15 min per email
- Google: 10 attempts per 5 min per IP

### 7. IP Address Tracking

```python
def get_client_ip(request):
    # Check X-Forwarded-For header (proxy-aware)
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.META.get("REMOTE_ADDR")

# Store di UserUsage.ip_address untuk:
# - Fraud detection
# - Geographic login alerts
# - Brute force from specific IP
```

### 8. Session Security

Django session config di `settings.py`:
```python
SESSION_ENGINE = 'django.contrib.sessions.backends.db'  # Store di database
SESSION_COOKIE_AGE = 1209600  # 2 weeks
SESSION_COOKIE_HTTPONLY = True  # Not accessible via JavaScript
SESSION_COOKIE_SECURE = False  # Set to True in production (HTTPS only)
SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection
```

---

## Dekorator & Proteksi Rute

### Cara Pakai Dekorator

**Contoh 1: `@guest_required` (public auth-only pages)**

```python
from accounts.decorators import guest_required

@guest_required
def sign_in(request):
    # Hanya guest (belum login) bisa akses
    # User authenticated → redirect ke home
```

**Contoh 2: `@verified_email_required` (workspace & core features - future)**

```python
from accounts.decorators import verified_email_required

@verified_email_required
def dashboard(request):
    # Hanya user authenticated + email verified bisa akses
    # User tidak login → redirect ke signin
    # User login tapi email belum verified → redirect ke email_unverified
```

### Stacking Multiple Decorators

```python
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from accounts.decorators import verified_email_required

@verified_email_required
@require_POST
def create_note(request):
    # Check order (bottom to top):
    # 1. require_POST: Method harus POST
    # 2. verified_email_required: User harus login & verified
    # 3. Eksekusi function
```

### Custom Decorator Pattern (untuk future)

Jika ingin membuat decorator baru:

```python
from functools import wraps
from django.contrib import messages

def my_feature_required(view_func):
    """Misal: hanya user dengan feature flag tertentu bisa akses"""
    
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('signin')
        
        if not request.user.profile.has_feature_x:
            messages.warning(request, "Fitur ini belum tersedia untuk Anda.")
            return redirect('home')
        
        return view_func(request, *args, **kwargs)
    
    return wrapper

# Usage:
@my_feature_required
def feature_x_view(request):
    ...
```

---

## Template & UI

### Auth-Aware Navigation (base.html)

```html
<!-- Jika user authenticated -->
{% if request.user.is_authenticated %}
    <a href="{% url 'project' %}">Go to Project</a>
    
    <!-- Logout button (contoh ditaruh di navbar/dropdown spesifik) -->
    <form method="post" action="{% url 'logout' %}">
        {% csrf_token %}
        <button type="submit">Logout</button>
    </form>

<!-- Jika user belum authenticated (guest) -->
{% else %}
    <!-- Show Sign In link -->
    <a href="{% url 'signin' %}">Sign In</a>
    
    <!-- Show Get Started button -->
    <a href="{% url 'signup' %}">Get Started</a>
{% endif %}
```

### Flash Messages

Notifikasi *toast* / popup pesan menggunakan styling tailwind dan berjalan secara global pada halaman utama seperti yang dicontohkan di `base.html`:

```html
<!-- Django messages framework otomatis via context_processors -->
{% if messages %}
<div class="fixed top-4 right-4 z-50 flex flex-col gap-2">
    {% for message in messages %}
    <div class="px-4 py-3 rounded shadow-lg text-sm text-white {% if message.tags == 'error' %}bg-red-600{% elif message.tags == 'success' %}bg-green-600{% else %}bg-blue-600{% endif %} transition-opacity duration-300 opacity-90 hover:opacity-100">
        {{ message }}
    </div>
    {% endfor %}
</div>
{% endif %}
```

**Template view:***
```python
from django.contrib import messages

messages.success(request, "Email berhasil diverifikasi.")
messages.error(request, "Password salah.")
messages.warning(request, "Email belum diverifikasi.")
```

### Form Rendering

```html
<!-- Simple form rendering -->
<form method="post">
    {% csrf_token %}
    {{ form.username }}
    {{ form.password }}
    <button type="submit">Login</button>
</form>

<!-- Manual rendering (more control) -->
<form method="post">
    {% csrf_token %}
    <input 
        type="text" 
        name="username"
        value="{{ form.username.value|default:'' }}"
        placeholder="Email atau Username"
    />
    {% if form.username.errors %}
        <span class="error">{{ form.username.errors.0 }}</span>
    {% endif %}
</form>
```

### List of Auth Templates

| Template | Purpose |
|----------|---------|
| `templates/signin.html` | Login form page |
| `templates/signup.html` | Registration form page |
| `templates/forgot_password.html` | Forgot password request |
| `templates/base.html` | Base layout (nav, messages, etc) |
| `templates/home.html` | Landing page |
| `templates/auth/email_unverified.html` | Verification gate |
| `templates/auth/email_verification_invalid.html` | Verification link expired |
| `templates/auth/password_reset_confirm.html` | Reset password form |
| `templates/auth/password_reset_invalid.html` | Reset link expired |

---

## Cara Menggunakan API

### Dalam Views

```python
from django.contrib.auth import get_user_model, login, logout
from accounts.decorators import guest_required, verified_email_required
from accounts.models import UserProfile, UserUsage
from accounts.utils import (
    is_email_verified,
    send_verification_email,
    get_login_usage,
    is_login_rate_limited,
)

User = get_user_model()

@verified_email_required
def my_protected_view(request):
    # request.user adalah user object
    # request.user.is_authenticated = True
    # request.user.profile.email_verified = True
    
    profile = request.user.profile
    usage = UserUsage.objects.get(user=request.user, date=today)
    
    return render(request, "my_template.html", {
        "user_email": request.user.email,
        "ai_usage": usage.prompt_count,
    })
```

### Dalam Templates

```html
<!-- Check authentication status -->
{% if request.user.is_authenticated %}
    <p>Welcome, {{ request.user.username }}!</p>
    <p>Email: {{ request.user.email }}</p>
    <p>Email verified: {{ AUTH_EMAIL_VERIFIED }}</p>
{% else %}
    <p>Please log in first.</p>
{% endif %}

<!-- Generate URLs secara dynamic -->
<a href="{% url 'signin' %}">Sign In</a>
<a href="{% url 'verify_email' uidb64=uid token=token %}">
    Verify Email
</a>
```

### Dalam Management Commands

```python
# File: accounts/management/commands/send_bulk_verification.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from accounts.utils import send_verification_email
from django.test import RequestFactory

User = get_user_model()

class Command(BaseCommand):
    def handle(self, *args, **options):
        unverified_users = User.objects.filter(
            profile__email_verified=False
        )
        
        # Create fake request untuk build absolute URLs
        factory = RequestFactory()
        request = factory.get('/')
        request.META['HTTP_HOST'] = 'example.com'
        request.META['wsgi.url_scheme'] = 'https'
        
        for user in unverified_users:
            send_verification_email(request, user)
            self.stdout.write(f"Sent to {user.email}")
```

### Admin Interface

```python
# File: accounts/admin.py
from django.contrib import admin
from .models import UserProfile, UserUsage

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'email_verified', 'created_at')
    list_filter = ('email_verified', 'created_at')
    search_fields = ('user__email', 'user__username')

@admin.register(UserUsage)
class UserUsageAdmin(admin.ModelAdmin):
    list_display = ('user', 'identifier', 'date', 'failed_login_count')
    list_filter = ('date',)
    search_fields = ('identifier', 'user__email')
```

---

## Async Email via Redis/RQ (Optional)

Jika ingin menghindari blocking saat kirim email (signup, resend verification, reset password), email dapat dikirim lewat Redis/RQ.

**Ringkasan implementasi:**
- Toggle dengan env `EMAIL_ASYNC=true`
- Job email dipush ke queue `default`
- Koneksi Redis baca dari env `REDIS_URL` (fallback localhost)
- Worker dijalankan via `python manage.py rqworker`

**Langkah setup (ringkas):**

1. Set env di runtime:
   ```bash
   export EMAIL_ASYNC=true
   export REDIS_URL=redis://localhost:6379/0
   ```

2. Jalankan Redis + worker:
   ```bash
   redis-server
   python manage.py rqworker
   ```

3. Pastikan backend email sudah valid (SMTP/SendGrid/Console backend).

**Catatan:**
- Mode async tetap memakai isi email yang sama; hanya cara pengirimannya yang dipindah ke queue.
- Jika Redis/worker mati, email tidak terkirim sampai worker aktif kembali.

---

## Troubleshooting

### Problem: Email tidak terkirim saat signup

**Possible causes:**

1. **Email backend tidak dikonfigurasi**
   ```python
   # settings.py
   EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'  # Development
   # atau
   EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'  # Production
   EMAIL_HOST = 'smtp.gmail.com'
   EMAIL_PORT = 587
   EMAIL_USE_TLS = True
   EMAIL_HOST_USER = 'your-email@gmail.com'
   EMAIL_HOST_PASSWORD = 'your-app-password'
   DEFAULT_FROM_EMAIL = 'noreply@mythosnote.com'
   ```

2. **Redis/RQ tidak running (jika pakai async email)**
   ```bash
   redis-server  # Start Redis
   python manage.py rqworker  # Start worker
   ```

3. **Mail folder permission issue**
   ```bash
   chmod -R 755 /path/to/maildir
   ```

**Solution:**

```bash
# Test email configuration
python manage.py shell
>>> from django.core.mail import send_mail
>>> send_mail(
...     "Test subject",
...     "Test message",
...     "from@example.com",
...     ["to@example.com"],
... )
1  # Should return 1 if success
```

---

### Problem: Rate limiting terlalu agresif / terlalu santai

**Edit di `accounts/utils.py`:**

```python
LOGIN_RATE_LIMIT_ATTEMPTS = 5          # Ubah ke 3 atau 10
LOGIN_RATE_LIMIT_WINDOW = timedelta(minutes=15)  # Ubah ke 5 atau 30
```

---

### Problem: Google OAuth token validation fail

**Check:**

1. **GOOGLE_OAUTH_CLIENT_ID salah**
   ```python
   # settings.py
   GOOGLE_OAUTH_CLIENT_ID = 'xxx.apps.googleusercontent.com'  # Dari Google Cloud Console
   ```

2. **Frontend token generation salah**
   ```html
   <!-- Pastikan Google library loaded -->
   <script src="https://accounts.google.com/gsi/client" async defer></script>
   
   <!-- Pastikan client_id dikirim ke button -->
   <div id="g_id_onload"
        data-client_id="YOUR_CLIENT_ID"
        data-callback="handleCredentialResponse">
   </div>
   ```

3. **CORS issue**
   - Tambah domain ke Google Cloud Console → Authorized domains

---

### Problem: Verification link expired tapi user belum klik

**Default token lifetime: 1 hari**

**Extend di `settings.py`:**

```python
PASSWORD_RESET_TIMEOUT = 86400  # seconds (default 1 day)
# Ubah ke 86400 * 7 untuk 7 hari
```

**Workaround:** User bisa click "Resend Verification" untuk dapat link baru.

---

### Problem: Terlalu banyak UserProfile records dibuat (signal issue)

**Check `accounts/signals.py`:**

```python
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import UserProfile

User = get_user_model()

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()
```

**Jika signal tidak auto-trigger, manual create:**

```bash
python manage.py shell
>>> from django.contrib.auth import get_user_model
>>> from accounts.models import UserProfile
>>> User = get_user_model()
>>> for user in User.objects.filter(profile__isnull=True):
...     UserProfile.objects.create(user=user)
```

---

### Problem: Session expired terlalu cepat / terlalu lama

**Edit di `settings.py`:**

```python
SESSION_COOKIE_AGE = 1209600  # Seconds (default: 2 weeks)
# Ubah ke 86400 untuk 1 hari
# Ubah ke 2592000 untuk 1 bulan

SESSION_EXPIRE_AT_BROWSER_CLOSE = False  # Session permanent sampai SESSION_COOKIE_AGE
```

---

### Problem: CSRF token missing / mismatch

**Ensure:**

1. **Form include `{% csrf_token %}`**
   ```html
   <form method="post">
       {% csrf_token %}  <!-- REQUIRED -->
       ...
   </form>
   ```

2. **Middleware enabled**
   ```python
   # settings.py
   MIDDLEWARE = [
       ...
       'django.middleware.csrf.CsrfViewMiddleware',  # ← Must be present
       ...
   ]
   ```

3. **Cookie setting**
   ```python
   CSRF_COOKIE_SECURE = False  # Set to True in production (HTTPS)
   CSRF_COOKIE_HTTPONLY = False  # Must be False (JavaScript need read)
   ```

---

### Problem: Password reset link tidak work

**Check:**

1. **Token valid?**
   - Token expire dalam `PASSWORD_RESET_TIMEOUT` hari (default 1 hari)
   - Jika user ubah password sebelum klik reset link → token invalid

2. **Test manual:**
   ```bash
   python manage.py shell
   >>> from django.contrib.auth import get_user_model
   >>> from django.contrib.auth.tokens import default_token_generator
   >>> User = get_user_model()
   >>> user = User.objects.first()
   >>> token = default_token_generator.make_token(user)
   >>> valid = default_token_generator.check_token(user, token)
   >>> print(valid)  # Should be True
   ```

---

### Problem: Email verification token invalid / expired (v1.1.2+)

**Perubahan v1.1.2:** Token di-sign dengan `profile.last_verification_email_sent_at`

**Penyebab token invalid:**
1. **User resend email verification** → `last_verification_email_sent_at` updated → token lama invalid
   - Solusi: User gunakan link dari email TERBARU
2. **User ubah password** → token invalid (standard Django behavior)
   - Solusi: Resend verification email lagi
3. **Token expired** (default 1 hari) → token invalid
   - Solusi: Click "Resend Verification" di halaman email_unverified

**Test token generator:**
```bash
python manage.py shell
>>> from accounts.utils import email_verification_token_generator
>>> from django.contrib.auth import get_user_model
>>> User = get_user_model()
>>> user = User.objects.first()
>>> token = email_verification_token_generator.make_token(user)
>>> valid = email_verification_token_generator.check_token(user, token)
>>> print(valid)  # Should be True
```

---

### Problem: User masih bisa login padahal email belum verified (v1.1.4)

**Perubahan v1.1.4:** User dibuat dengan `is_active=False`, tidak bisa login sampai email verified.

**Check:**
1. **Signup tidak buat user dengan is_active=False**
   - Solusi: Update SignUpForm.save() untuk set `user.is_active = False`
   
2. **Login tidak check inactive user**
   - Solusi: SignInForm.clean() harus check `is_active=False` users & send verification email

```python
# Debug di shell:
>>> from django.contrib.auth import get_user_model
>>> User = get_user_model()
>>> user = User.objects.first()
>>> print(f"is_active: {user.is_active}")
>>> print(f"email_verified: {user.profile.email_verified}")
```

---

### Problem: Email validator reject valid email (v1.1.2+)

**Library:** `email-validator` (strict validation)

**Issue:** Email dengan domain valid tapi sedikit unconventional bisa di-reject.

**Solusi:**

1. **Check error message:**
   ```bash
   python manage.py shell
   >>> from accounts.validators import validate_real_email
   >>> try:
   ...     validate_real_email("user@example.com")
   ... except Exception as e:
   ...     print(e)
   ```

2. **Disable MX check (tidak recommended):**
   ```python
   # accounts/validators.py
   result = validate_email(email, check_deliverability=False)
   # Tapi jadi tidak jadi check MX records
   ```

---

### Problem: Cleanup command tidak menghapus user (v1.1.5)

**Command:** `python manage.py cleanup_unverified_users`

**Debug:**
```bash
# Dry-run untuk lihat siapa yang akan dihapus:
python manage.py cleanup_unverified_users --dry-run

# Check criteria di database:
python manage.py shell
>>> from django.contrib.auth import get_user_model
>>> User = get_user_model()
>>> from datetime import timedelta, timezone
>>> cutoff = timezone.now() - timedelta(days=1)
>>> candidates = User.objects.filter(
...     is_active=False,
...     profile__email_verified=False,
...     date_joined__lte=cutoff
... )
>>> print(f"Total candidates: {candidates.count()}")
>>> for user in candidates:
...     print(f"- {user.email} (joined {user.date_joined})")
```

---

### Problem: Google OAuth tidak auto-mark email_verified (v1.1.1)

**Perubahan v1.1.1:** User dari Google OAuth sekarang otomatis marked sebagai email_verified.

**Check:**
1. **Google token harus punya `email_verified: True`**
   ```python
   # Inspect di view:
   payload = verify_google_credential(credential)
   print(f"email_verified: {payload.get('email_verified')}")
   ```

2. **User already existed sebelum update?**
   - Google OAuth tidak auto-update existing users
   - Solusi: Manual update di admin atau shell:
   ```python
   >>> user = User.objects.get(email="google-user@gmail.com")
   >>> user.profile.email_verified = True
   >>> user.profile.save()
   ```

---

## Best Practices

### 1. User Identification

```python
# ❌ JANGAN: Sensitive info di URL/cookie
GET /user/123  # Attacker bisa guess other user IDs

# ✅ GUNAKAN: Relasi via session
GET /my-profile  # Backend get dari session user
```

### 2. Email Validation

```python
# ❌ JANGAN: Send email tanpa verify domain
# Pengguna bisa input email orang lain

# ✅ GUNAKAN: Token link
# User harus klik link di email mereka, buktian email ownership
```

### 3. Password Storage

```python
# ❌ JANGAN: Store password plaintext
user.password = "secret123"
user.save()

# ✅ GUNAKAN: Django's set_password()
user.set_password("secret123")
user.save()
# Otomatis hash dengan PBKDF2
```

### 4. Rate Limiting Scope

```python
# Track by:
# - Username/email + date (account enumeration protection)
# - IP + date (brute force from same IP)
# - Combination untuk better accuracy
```

### 5. Secure Communication

```python
# Production settings:
SESSION_COOKIE_SECURE = True  # HTTPS only
SESSION_COOKIE_HTTPONLY = True  # No JavaScript access
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
```

---

## Struktur File Summary

```
accounts/
├── models.py                 # UserProfile, UserUsage
├── views.py                  # Auth views (signin, signup, etc)
├── forms.py                  # Form validation
├── decorators.py             # @guest_required, @verified_email_required
├── utils.py                  # Helper functions
├── urls.py                   # Auth routing
├── context_processors.py     # Template context injection
├── admin.py                  # Admin interface (optional)
├── signals.py                # Auto-create UserProfile (optional)
├── apps.py                   # App config
├── tests.py                  # Unit tests (optional)
└── migrations/
    └── 0001_initial.py       # Database schema

config/
├── settings.py               # Email config, middleware
├── urls.py                   # Include accounts.urls
└── views.py                  # Landing page

templates/
├── base.html                 # Auth-aware nav
├── signin.html
├── signup.html
├── forgot_password.html
├── home.html
└── auth/
    ├── email_unverified.html
    ├── email_verification_invalid.html
    └── password_reset_confirm.html
    └── password_reset_invalid.html
```

---

## Kesimpulan

Sistem autentikasi MythosNote dibangun dengan:

✅ **Security first:**
- Password hashing (PBKDF2)
- Rate limiting (5 attempts / 15 min)
- CSRF protection
- Signed token URLs (tidak reusable)
- Email verification gate

✅ **User-friendly:**
- Signup & login mudah
- Google OAuth option
- Clear error messages
- Resend verification link
- Forgot password flow

✅ **Scalable:**
- `UserUsage` model siap untuk kuota AI
- Dekorator future-ready untuk workspace/core features
- Per-day tracking siap untuk analytics

✅ **Maintainable:**
- Terpisah ke models, views, forms, utils
- Reusable decorator pattern
- Clear function responsibilities

Dokumentasi ini mudah dipelajari dan bisa diperluas sesuai kebutuhan project lebih lanjut!
