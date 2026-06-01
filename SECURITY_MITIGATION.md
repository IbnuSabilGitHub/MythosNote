# Mitigasi Keamanan - AI Quota & Rate Limiting

## Celah Keamanan yang Ditemukan

1. **Race Condition** - Pengecekan kuota dan inkrementasi tidak atomik sempurna
2. **Pembatasan Tidak Sinkron** - Throttling DRF dan pengecekan kuota harian terpisah
3. **Tracking Identitas Lemah** - Hanya mengandalkan email/IP, mudah diakali dengan akun baru
4. **Tidak Ada Batas Concurrent Requests** - Pengguna bisa mengirim banyak request paralel
5. **Minimnya Device Fingerprinting** - Tidak ada identifikasi perangkat yang kuat

## Mitigasi KRITIS yang Telah Diimplementasikan

### 1. Update Atomik dengan WHERE Condition (Mencegah Race Condition)

**File**: `apps/accounts/utils.py`

```python
# Sebelumnya (rentan race condition):
with transaction.atomic():
    usage = get_api_usage(user, request)
    locked_usage = UserUsage.objects.select_for_update().get(pk=usage.pk)
    if locked_usage.prompt_count >= settings.AI_DAILY_PROMPT_LIMIT:
        return False
    locked_usage.prompt_count = F("prompt_count") + 1
    locked_usage.save(update_fields=["prompt_count"])

# Sekarang (aman dari race condition):
updated = UserUsage.objects.filter(
    user=user,
    identifier=identifier,
    date=today,
    prompt_count__lt=settings.AI_DAILY_PROMPT_LIMIT,  # Kondisi WHERE atomik
).update(
    prompt_count=F("prompt_count") + 1,
    last_request_at=timezone.now(),
    device_fingerprint=device_fingerprint,
)

if updated == 0:
    # Kuota sudah habis atau record baru perlu dibuat
    return False
```

**Keuntungan**: Database menangani locking secara internal, tidak ada window untuk race condition.

### 2. Device Fingerprinting (Mencegah Pembuatan Akun Ganda)

**File**: `apps/accounts/utils.py`

```python
def generate_device_fingerprint(request: HttpRequest) -> str:
    """Generate fingerprint dari User-Agent, Accept-Language, Accept-Encoding."""
    user_agent = request.META.get("HTTP_USER_AGENT", "")
    accept_language = request.META.get("HTTP_ACCEPT_LANGUAGE", "")
    accept_encoding = request.META.get("HTTP_ACCEPT_ENCODING", "")
    
    fingerprint_data = f"{user_agent}|{accept_language}|{accept_encoding}"
    return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:64]
```

**Model Update** (`apps/accounts/models.py`):
- Menambahkan field `device_fingerprint` dengan index
- Track fingerprint per permintaan untuk deteksi pola mencurigakan

### 3. Concurrent Request Limiting (Mencegah Serangan Paralel)

**File**: `apps/accounts/utils.py`

```python
MAX_CONCURRENT_REQUESTS = 5
CONCURRENT_REQUEST_WINDOW = timedelta(seconds=10)

def check_concurrent_request_limit(user: Any, request: HttpRequest) -> bool:
    """Cek apakah user melebihi batas request bersamaan menggunakan cache."""
    if not user.is_authenticated:
        return True
    
    cache_key = f"concurrent_requests:{user.pk}"
    current_count = cache.get(cache_key, 0)
    
    if current_count >= MAX_CONCURRENT_REQUESTS:
        return False
    
    cache.set(cache_key, current_count + 1, int(CONCURRENT_REQUEST_WINDOW.total_seconds()))
    return True

def release_concurrent_request(user: Any, request: HttpRequest) -> None:
    """Release slot setelah request selesai."""
    cache_key = f"concurrent_requests:{user.pk}"
    current_count = cache.get(cache_key, 0)
    if current_count > 0:
        cache.set(cache_key, current_count - 1, int(CONCURRENT_REQUEST_WINDOW.total_seconds()))
```

**Implementasi di check_and_increment_prompt**:
```python
def check_and_increment_prompt(user: Any, request: HttpRequest) -> bool:
    if not check_concurrent_request_limit(user, request):
        return False  # Tolak jika sudah ada 5 request berjalan
    
    try:
        # ... proses quota check ...
        return True
    finally:
        release_concurrent_request(user, request)  # Selalu release slot
```

### 4. Tracking Tambahan untuk Audit

**Model Update** (`apps/accounts/models.py`):
- `concurrent_requests`: Counter untuk monitoring
- `last_request_at`: Timestamp request terakhir
- Index baru untuk query performa tinggi

### 5. Lapisan Pertahanan Berlapis

Setiap fungsi quota sekarang memiliki:
1. **Layer 1**: Concurrent request check (cache-based, cepat)
2. **Layer 2**: Atomic database update dengan kondisi WHERE
3. **Layer 3**: Device fingerprint tracking
4. **Layer 4**: Proper cleanup di finally block

## Migration Database

File migration baru: `apps/accounts/migrations/0006_add_device_fingerprint_and_concurrent_tracking.py`

```bash
python manage.py migrate accounts
```

## Konfigurasi yang Dapat Disesuaikan

Di `apps/accounts/utils.py`:
```python
MAX_CONCURRENT_REQUESTS = 5  # Sesuaikan berdasarkan kapasitas server
CONCURRENT_REQUEST_WINDOW = timedelta(seconds=10)  # Window untuk concurrent tracking
```

Di `config/settings.py`:
```python
AI_DAILY_PROMPT_LIMIT = 50
AI_DAILY_GENERATE_LIMIT = 20
AI_DAILY_UPLOAD_LIMIT = 10
```

## Testing

```bash
# Test device fingerprint generation
SECRET_KEY="test" DJANGO_SETTINGS_MODULE=config.settings python -c "
import django; django.setup()
from apps.accounts.utils import generate_device_fingerprint
from django.http import HttpRequest
req = HttpRequest()
req.META['HTTP_USER_AGENT'] = 'Mozilla/5.0'
req.META['HTTP_ACCEPT_LANGUAGE'] = 'en-US'
req.META['REMOTE_ADDR'] = '127.0.0.1'
print(generate_device_fingerprint(req))
"
```

## Rekomendasi Tambahan (Future Improvements)

1. **Redis-based Rate Limiting**: Gunakan Redis untuk distributed rate limiting jika ada multiple servers
2. **Machine Learning Anomaly Detection**: Deteksi pola penggunaan tidak wajar
3. **IP Reputation Database**: Integrasikan dengan layanan blacklist IP
4. **Progressive Penalties**: Tingkatkan durasi blocking untuk pelanggar berulang
5. **Real-time Monitoring Dashboard**: Dashboard untuk memantau quota usage per user

## File yang Dimodifikasi

1. `apps/accounts/models.py` - Tambah field tracking
2. `apps/accounts/utils.py` - Implementasi mitigasi lengkap
3. `apps/accounts/migrations/0006_*.py` - Migration baru

## Prioritas Implementasi

✅ **KRITIS** (Sudah diimplementasikan):
- Atomic update dengan WHERE condition
- Concurrent request limiting
- Device fingerprinting

⏳ **TINGGI** (Rekomendasi selanjutnya):
- Redis-based distributed locking
- Audit logging untuk suspicious patterns
- Alerting untuk quota abuse

⏳ **SEDANG** (Future improvements):
- Machine learning anomaly detection
- Progressive penalties
- Admin dashboard monitoring
