# Changelog

Semua perubahan penting di MythosNote dicatat di sini. Format mengikuti [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) dan versioning [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


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
