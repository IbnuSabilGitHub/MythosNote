# 📚 Dokumentasi Sistem Autentikasi MythosNote

Selamat datang di dokumentasi sistem autentikasi MythosNote! Dokumentasi ini telah diorganisir secara modular untuk memudahkan navigasi dan pemahaman.

## 🗂️ Struktur Dokumentasi

### 1. **Dasar-Dasar (Fundamentals)**
- [**01-pengenalan.md**](./01-pengenalan.md) - Pengenalan sistem autentikasi dan konsep dasar
- [**02-arsitektur-database.md**](./02-arsitektur-database.md) - Model database, relasi, dan constraint
- [**03-alur-autentikasi.md**](./03-alur-autentikasi.md) - Diagram dan alur lengkap sistem

### 2. **Implementasi (Implementation)**
- [**04-komponen-utama.md**](./04-komponen-utama.md) - Komponen kode: models, views, forms
- [**05-dekorator-proteksi.md**](./05-dekorator-proteksi.md) - Dekorator dan proteksi rute
- [**06-alur-fitur-detail.md**](./06-alur-fitur-detail.md) - Alur terperinci setiap fitur (signup, signin, dll)

### 3. **Keamanan & Konfigurasi (Security & Configuration)**
- [**07-keamanan-rate-limiting.md**](./07-keamanan-rate-limiting.md) - Rate limiting dan security best practices
- [**08-email-async.md**](./08-email-async.md) - Pengiriman email asynchronous via Redis/RQ

### 4. **Frontend & API**
- [**09-template-ui.md**](./09-template-ui.md) - Template HTML dan komponen UI
- [**10-api-usage.md**](./10-api-usage.md) - Cara menggunakan API endpoints

### 5. **Troubleshooting & Maintenance**
- [**11-troubleshooting.md**](./11-troubleshooting.md) - Common issues dan solusi
- [**12-best-practices.md**](./12-best-practices.md) - Best practices dan tips

## 🚀 Quick Start

Jika Anda baru mengenal sistem ini, ikuti urutan berikut:

1. **Pemula?** → Mulai dari [Pengenalan](./01-pengenalan.md)
2. **Ingin memahami database?** → Baca [Arsitektur Database](./02-arsitektur-database.md)
3. **Implementasi fitur?** → Lihat [Alur Fitur Detail](./06-alur-fitur-detail.md)
4. **Troubleshooting?** → Langsung ke [Troubleshooting](./11-troubleshooting.md)

## 📋 Ringkasan Sistem

MythosNote mengimplementasikan sistem autentikasi lengkap dengan:

- ✅ Registrasi akun baru (Sign Up)
- ✅ Login dengan email/username dan password (Sign In)
- ✅ Verifikasi email wajib
- ✅ Reset password via email
- ✅ Google OAuth integration
- ✅ Rate limiting (5 attempts / 15 menit)
- ✅ Session management
- ✅ Usage tracking untuk kuota AI

## 🛠️ Tech Stack

- **Backend:** Django 5.1+
- **Database:** PostgreSQL / SQLite
- **Email:** SMTP / Gmail
- **OAuth:** Google OAuth 2.0
- **Queue (Optional):** Redis + RQ
- **Frontend:** Bootstrap 5 + vanilla JavaScript

## 📞 Kontak & Dukungan

Jika ada pertanyaan atau menemukan masalah:
1. Cek [Troubleshooting Guide](./11-troubleshooting.md)
2. Review [Best Practices](./12-best-practices.md)
3. Buka issue di repository

---

**Last Updated:** 13 May 2024  