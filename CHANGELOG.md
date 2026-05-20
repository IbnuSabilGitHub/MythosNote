# Changelog

Semua perubahan penting di MythosNote dicatat di sini. Format mengikuti [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) dan versioning [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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