# Bukti Konkret — Stored XSS Full Chain PoC

Pengujian **hanya di https://mythosnote.tech milik sendiri** dengan 2 akun:
- **Attacker** — siapkan webhook, edit stage 2
- **Korban** — akun terpisah (incognito), tidak tahu isi payload

---

## Persiapan

1. Buat akun **korban** baru (email berbeda dari admin).
2. Buka https://webhook.site → salin UUID.
3. Di `e2e-xss-stage1-recon.txt` ganti `WEBHOOK_UUID`.
4. Siapkan 2+ file dummy di workspace korban (supaya delete stage 2 tidak menghapus satu-satunya file penting).

---

## Fase 1 — Recon (Attacker kirim file ke Korban)

```
Attacker: edit stage1 → kirim e2e-xss-stage1-recon.txt ke Korban
Korban:   login → workspace → upload file → generate Mindmap → buka hasil
```

### Bukti yang harus dikumpulkan

| # | Bukti | Cara dapat |
|---|-------|------------|
| 1 | Payload masuk DB | DevTools → `/api/generate/{id}/` → `result` ada `</script>` |
| 2 | Webhook STAGE1_RECON | webhook.site → JSON: `email`, `workspace_id`, `sources`, `quota` |
| 3 | Screenshot overlay | Halaman mindmap korban: "FASE 1 RECON SELESAI" |
| 4 | CSRF preview | Field `csrf_token_preview` di webhook (bukan session cookie) |

**Catat dari webhook:**
- `workspace_id`
- `sources.results[0].id` (pilih source **bukan** file PoC)

---

## Fase 2 — Abuse (Attacker edit template, kirim lagi)

1. Copy `e2e-xss-stage2-abuse.txt`
2. Ganti:
   - `__WORKSPACE_ID__` → dari webhook fase 1
   - `__SOURCE_ID__` → id source korban
   - `WEBHOOK_UUID` → UUID webhook
3. Kirim file stage 2 ke korban (file **baru**, upload ulang).
4. Korban: generate Mindmap → buka hasil.

### Bukti yang harus dikumpulkan

| # | Bukti | Cara dapat |
|---|-------|------------|
| 5 | Webhook STAGE2_ABUSE | `actions`: 3× `generate_spam`, 1× `delete_source` status 204 |
| 6 | Email korban | Field `email` di webhook |
| 7 | Password phishing | Korban ketik password dummy di overlay → field `password_phish` di webhook |
| 8 | Source terhapus | Workspace korban: file target hilang dari daftar |
| 9 | Kuota habis | Panel kuota korban naik / sisa generate berkurang |
| 10 | Screenshot overlay phishing | "Sesi Berakhir" + form password |

---

## Bukti bahwa CSRF curian TIDAK bisa dipakai dari laptop hacker

Jalankan di mesin attacker (**harus gagal**):

```bash
# Ambil csrf_token_preview + source id dari webhook — TANPA session cookie korban
export STOLEN_CSRF="isi_csrftoken_dari_webhook_lengkap_jika_ada"
export SOURCE_ID="uuid-source-korban"

curl -s -o /dev/null -w "%{http_code}" -X DELETE \
  "https://mythosnote.tech/api/sources/${SOURCE_ID}/" \
  -H "X-CSRFToken: ${STOLEN_CSRF}" \
  -H "Accept: application/json"
# Harapan: 403 atau 401 — BUKAN 204
```

Screenshot output `403` = bukti **sessionid HttpOnly** melindungi dari replay remote.
Abuse hanya jalan **di browser korban** (fase 2 XSS).

---

## Password — apa yang bisa / tidak bisa dibuktikan

| Data | Via XSS/API | Bukti |
|------|-------------|-------|
| Email | ✅ | Scrape `/settings/` → webhook `email` |
| Nama | ✅ | webhook `first_name` |
| Password hash / plaintext | ❌ | Tidak pernah di response API |
| Password (phishing) | ✅ PoC | Overlay fase 2 → `password_phish` di webhook |

Tulis di laporan: *"Password database tidak bocor; XSS enables credential phishing overlay."*

---

## Checklist laporan final

- [ ] Fase 1 webhook JSON (screenshot)
- [ ] Fase 2 webhook JSON dengan `actions` + `password_phish`
- [ ] Before/after screenshot daftar source (delete)
- [ ] Before/after screenshot kuota generate
- [ ] curl replay gagal (403)
- [ ] View-source halaman mindmap menunjukkan `|safe` breakout
- [ ] Catatan: link quiz **tidak** shareable antar user (404)

---

## Urutan roleplay

```
[Hacker]  buat webhook + edit stage1
    ↓
[Korban]  upload stage1 → mindmap → buka
    ↓
[Webhook] STAGE1_RECON (email, workspace_id, source ids)
    ↓
[Hacker]  edit stage2 dengan id dari webhook
    ↓
[Korban]  upload stage2 → mindmap → buka → isi password di overlay
    ↓
[Webhook] STAGE2_ABUSE (delete + spam + password_phish)
    ↓
[Hacker]  curl replay GAGAL → bukti HttpOnly works
```
