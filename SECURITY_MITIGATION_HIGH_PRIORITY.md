# Mitigasi Keamanan - Prioritas TINGGI

## Ringkasan Eksekutif

Setelah mitigasi KRITIS (race condition, device fingerprinting, concurrent request limiting) berhasil diimplementasikan, dokumen ini menjelaskan mitigasi prioritas **TINGGI** yang telah ditambahkan untuk memperkuat sistem limitasi AI quota.

## Celah Keamanan Prioritas TINGGI yang Ditemukan

1. **Fixed Window Rate Limiting** - Counter berbasis fixed window (per hari) tidak mencegah spam dalam jangka pendek (per menit/detik)
2. **Tidak Ada Burst Control** - Pengguna bisa mengirim semua request sekaligus di awal periode
3. **Tidak Ada Graduated Throttling** - Semua jenis request diperlakukan sama, padahal generate/upload lebih mahal daripada prompt
4. **Tidak Ada Visibility** - User dan admin tidak bisa melihat sisa quota real-time

## Mitigasi Prioritas TINGGI yang Telah Diimplementasikan

### 1. Sliding Window Rate Limiting (Per Menit)

**File**: `apps/accounts/utils.py`

```python
SLIDING_WINDOW_SIZE = timedelta(minutes=1)
SLIDING_WINDOW_MAX_REQUESTS = 10  # Max 10 request per menit

def check_sliding_window_rate_limit(user: Any, request: HttpRequest) -> bool:
    """Menggunakan Redis sorted set untuk tracking timestamp request."""
    cache_key = f"sliding_window:{user.pk}"
    now = timezone.now().timestamp()
    window_start = now - SLIDING_WINDOW_SIZE.total_seconds()
    
    # Hapus request lama di luar window
    cache.zremrangebyscore(cache_key, '-inf', window_start)
    
    # Hitung request dalam window
    current_count = cache.zcard(cache_key)
    
    if current_count >= SLIDING_WINDOW_MAX_REQUESTS:
        return False
    
    # Tambahkan request baru dengan timestamp sebagai score
    member = f"{now}:{id(request)}"
    cache.zadd(cache_key, {member: now})
    cache.expire(cache_key, int(SLIDING_WINDOW_SIZE.total_seconds() * 2))
    
    return True
```

**Keuntungan**:
- Akurasi tinggi dibanding fixed window counter
- Mencegah spam dalam jangka pendek (10 req/menit)
- Cleanup otomatis dengan TTL
- Menggunakan Redis sorted set untuk performa tinggi

### 2. Token Bucket Algorithm (Burst Control)

**File**: `apps/accounts/utils.py`

```python
TOKEN_BUCKET_CAPACITY = 20  # Kapasitas maksimum token
TOKEN_BUCKET_REFILL_RATE = 2  # 2 token per detik

def check_token_bucket(user: Any, request: HttpRequest, tokens_required: int = 1) -> bool:
    """Token bucket memberikan fleksibilitas untuk burst traffic sambil menjaga rata-rata rate."""
    cache_key = f"token_bucket:{user.pk}"
    now = timezone.now().timestamp()
    
    # Ambil state bucket
    bucket_data = cache.get(cache_key)
    
    if bucket_data is None:
        tokens = TOKEN_BUCKET_CAPACITY
        last_update = now
    else:
        tokens, last_update = bucket_data
        # Refill token berdasarkan waktu yang berlalu
        time_passed = now - last_update
        tokens_to_add = time_passed * TOKEN_BUCKET_REFILL_RATE
        tokens = min(TOKEN_BUCKET_CAPACITY, tokens + tokens_to_add)
    
    if tokens < tokens_required:
        return False
    
    # Konsumsi token
    tokens -= tokens_required
    cache.set(cache_key, (tokens, now), timeout=3600)
    
    return True
```

**Konfigurasi Token per Operasi**:
- **Prompt/Chat**: 1 token (operasi ringan)
- **Generate**: 2 token (operasi medium - summary, mindmap, quiz, table)
- **Upload**: 3 token (operasi berat - pemrosesan file)

**Keuntungan**:
- Memungkinkan burst traffic yang terkontrol (sampai 20 request sekaligus jika bucket penuh)
- Menjaga rata-rata rate pada 2 request/detik (120 req/menit)
- Differentiasi biaya operasi berdasarkan kompleksitas
- Smooth rate limiting tanpa "cliff effect"

### 3. Defense in Depth - 4 Lapisan Pertahanan

Setiap fungsi `check_and_increment_*` sekarang memiliki 4 lapisan:

```python
def check_and_increment_prompt(user, request):
    # Layer 1: Concurrent request limit (mencegah serangan paralel)
    if not check_concurrent_request_limit(user, request):
        return False
    
    # Layer 2: Sliding window rate limit (mencegah spam per-menit)
    if not check_sliding_window_rate_limit(user, request):
        release_concurrent_request(user, request)
        return False
    
    # Layer 3: Token bucket (burst control dengan differentiated cost)
    if not check_token_bucket(user, request, tokens_required=1):
        release_concurrent_request(user, request)
        return False
    
    # Layer 4: Daily quota dengan atomic update (batas harian total)
    try:
        with transaction.atomic():
            updated = UserUsage.objects.filter(
                user=user,
                date=today,
                prompt_count__lt=settings.AI_DAILY_PROMPT_LIMIT,
            ).update(
                prompt_count=F("prompt_count") + 1,
                ...
            )
            ...
    finally:
        release_concurrent_request(user, request)
```

**Fungsi yang Diupdate**:
- `check_and_increment_prompt()` - 1 token untuk chat/prompt
- `check_and_increment_generate()` - 2 token untuk generate (summary, mindmap, quiz, table)
- `check_and_increment_upload()` - 3 token untuk upload file

### 4. API Endpoint untuk Monitoring Quota

**File**: `apps/accounts/utils.py`

```python
def get_remaining_tokens(user: Any) -> dict:
    """Memberikan visibility real-time tentang sisa quota."""
    return {
        "remaining_tokens": int(tokens),
        "max_tokens": TOKEN_BUCKET_CAPACITY,
        "refill_rate": TOKEN_BUCKET_REFILL_RATE,
        "requests_in_window": requests_in_window,
        "max_requests_per_minute": SLIDING_WINDOW_MAX_REQUESTS,
    }
```

**Rekomendasi Implementasi API** (belum diimplementasikan):
```python
# Tambahkan endpoint di views.py
@api_view(['GET'])
def quota_status(request):
    status = get_remaining_tokens(request.user)
    return Response(status)
```

## Perbandingan Sebelum dan Sesudah

| Metrik | Sebelum | Setelah |
|--------|---------|---------|
| **Rate Limiting** | Hanya harian (fixed window) | Harian + Per menit (sliding window) + Token bucket |
| **Burst Handling** | Tidak ada kontrol | Terkontrol (max 20 burst, refill 2/detik) |
| **Differentiated Cost** | Semua operasi sama | Prompt=1, Generate=2, Upload=3 token |
| **Akurasi** | Fixed window (bisa ditembus) | Sliding window log (akurat) |
| **Visibility** | Tidak ada | Real-time quota status tersedia |
| **Lapisan Keamanan** | 2 (concurrent + daily) | 4 (concurrent + sliding + bucket + daily) |

## Skenario Serangan yang Sekarang Dicegah

### 1. Spam Request dalam 1 Menit
**Sebelum**: User bisa mengirim 50 request dalam 1 menit asalkan kuota harian masih ada.
**Setelah**: Dibatasi max 10 request/menit oleh sliding window.

### 2. Burst Attack di Awal Periode
**Sebelum**: User bisa menggunakan semua 50 quota dalam 1 detik di tengah malam.
**Setelah**: Token bucket membatasi burst max 20 request, kemudian refill 2/detik.

### 3. Resource Exhaustion dengan Generate/Upload
**Sebelum**: Generate dan upload dihitung sama dengan prompt.
**Setelah**: Generate butuh 2x token, upload butuh 3x token dari bucket.

### 4. Parallel Request Flood
**Sebelum**: Sudah dicegah oleh mitigasi KRITIS (concurrent request limit).
**Setelah**: Tetap dicegah, ditambah dengan sliding window dan token bucket.

## Konfigurasi yang Dapat Disesuaikan

Di `apps/accounts/utils.py`:

```python
# Sliding window settings
SLIDING_WINDOW_SIZE = timedelta(minutes=1)  # Durasi window
SLIDING_WINDOW_MAX_REQUESTS = 10  # Max request per window

# Token bucket settings
TOKEN_BUCKET_CAPACITY = 20  # Kapasitas maksimum
TOKEN_BUCKET_REFILL_RATE = 2  # Token per detik

# Token cost per operasi
# - check_and_increment_prompt: tokens_required=1
# - check_and_increment_generate: tokens_required=2
# - check_and_increment_upload: tokens_required=3
```

## Testing & Validasi

### Unit Test yang Direkomendasikan

```python
def test_sliding_window_blocks_spam():
    """Test bahwa sliding window memblokir >10 request/menit."""
    for i in range(10):
        assert check_sliding_window_rate_limit(user, request) == True
    
    # Request ke-11 harus diblokir
    assert check_sliding_window_rate_limit(user, request) == False

def test_token_bucket_allows_burst():
    """Test bahwa token bucket mengizinkan burst sampai kapasitas."""
    for i in range(20):
        assert check_token_bucket(user, request) == True
    
    # Request ke-21 harus diblokir (bucket kosong)
    assert check_token_bucket(user, request) == False

def test_token_bucket_refills():
    """Test bahwa token bucket refill seiring waktu."""
    # Kosongkan bucket
    for i in range(20):
        check_token_bucket(user, request)
    
    # Tunggu 5 detik (harus refill 10 token)
    time.sleep(5)
    
    # Sekarang harus bisa lagi
    assert check_token_bucket(user, request) == True

def test_differentiated_token_cost():
    """Test bahwa generate/upload butuh lebih banyak token."""
    # Prompt hanya butuh 1 token
    assert check_token_bucket(user, request, tokens_required=1) == True
    
    # Generate butuh 2 token
    # ...test logic...
```

## Monitoring & Alerting

**Metrics yang Harus Dimonitor**:
1. Jumlah request yang diblokir per layer (concurrent, sliding, bucket, daily)
2. Rata-rata token tersisa per user
3. Peak request rate per user
4. Pattern mencurigakan (user yang consistently hitting limits)

**Alert Thresholds**:
- User diblokir >100 kali/jam → Potensi abuse
- Token bucket consistently empty → Mungkin perlu adjust capacity
- Sliding window consistently full → Mungkin perlu adjust limit

## Dokumentasi Tambahan

- **File Modified**: `apps/accounts/utils.py`
- **New Functions**: 
  - `check_sliding_window_rate_limit()`
  - `check_token_bucket()`
  - `get_remaining_tokens()`
- **Updated Functions**:
  - `check_and_increment_prompt()` - Added layers 2 & 3
  - `check_and_increment_generate()` - Added layers 2 & 3
  - `check_and_increment_upload()` - Added layers 2 & 3
- **New Constants**:
  - `SLIDING_WINDOW_SIZE`
  - `SLIDING_WINDOW_MAX_REQUESTS`
  - `TOKEN_BUCKET_CAPACITY`
  - `TOKEN_BUCKET_REFILL_RATE`
  - `TOKEN_BUCKET_KEY_PREFIX`

## Langkah Selanjutnya (Prioritas SEDANG)

1. **Tambahkan Endpoint API** untuk quota status
2. **Implementasi Audit Logging** untuk pattern detection
3. **Dashboard Admin** untuk monitoring usage patterns
4. **Machine Learning Anomaly Detection** untuk mendeteksi abuse patterns
5. **Graceful Degradation** untuk user yang mendekati limit (beri warning)

## Referensi

- [Token Bucket Algorithm](https://en.wikipedia.org/wiki/Token_bucket)
- [Sliding Window Log](https://en.wikipedia.org/wiki/Rate_limiting#Sliding_window_log)
- [OWASP Rate Limiting Guidelines](https://cheatsheetseries.owasp.org/cheatsheets/Denial_of_Service_Cheat_Sheet.html#rate-limiting)
