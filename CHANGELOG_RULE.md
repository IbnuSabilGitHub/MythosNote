# Changelog

Semua perubahan penting di MythosNote dicatat di sini. Format mengikuti [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) dan versioning [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## Cara Menulis Versi

Gunakan format `MAJOR.MINOR.PATCH`:
- **MAJOR** – Perubahan yang tidak kompatibel dengan versi sebelumnya.
- **MINOR** – Fitur baru, tetap kompatibel.
- **PATCH** – Perbaikan bug, tetap kompatibel.

---

## Kategori Perubahan

Setiap rilis harus punya kategori ini (jika ada):
- **Added** – Fitur baru.
- **Changed** – Perubahan pada fitur lama.
- **Deprecated** – Fitur yang akan segera dihapus.
- **Removed** – Fitur yang sudah dihapus.
- **Fixed** – Perbaikan bug.
- **Security** – Perbaikan keamanan.

---

## Format Commit

Ikuti [Conventional Commits](https://www.conventionalcommits.org/):
```
<type>[optional scope]: <description>

[optional body]

```

### Tipe Commit
- `feat` – Fitur baru.
- `fix` – Perbaikan bug.
- `docs` – Perubahan dokumentasi.
- `style` – Format kode.
- `refactor` – Perombakan kode tanpa fitur baru.
- `perf` – Peningkatan performa.
- `test` – Penambahan tes.
- `chore` – Build, dependensi, tools.

### Contoh
```
feat(sources): implementasi pemrosesan file async

- Tambah worker background untuk upload file.
- Implementasi chunking 500-800 token.
- Pipeline embedding otomatis.

```

---

## Aturan Penting
- Selalu update CHANGELOG sebelum merge PR.
- Jangan tunda penulisan sampai akhir sprint.
- Jelaskan alasan perubahan, bukan hanya apa yang diubah.