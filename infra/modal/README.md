# Konfigurasi Inference Modal GPU + vLLM (`infra/modal`) — Issue #26 (`OPS-04`)

Direktori ini berisi skrip deployment serverless GPU **Modal + vLLM** untuk menyajikan **SLM/LLM open-source OpenAI-compatible API** khusus bagi modul **AI Business Insight (`AI-06`)** pada `apps/ai-service`.

> **Batas Arsitektur & Keamanan (Project Plan A26-CS105):**
>
> - Endpoint GPU ini **hanya** digunakan untuk **AI Business Insight (`AI-06`)** dan **dilarang** digunakan untuk menggantikan API LLM proprietary pada chatbot Agentic RAG (`AI-05`).
> - Seluruh kredensial (`MODAL_API_KEY` / `HF_TOKEN`) dikelola melalui **Modal Secrets** dan environment variable server, **tidak pernah** di-commit ke Git.
> - Container menerapkan **scale-to-zero otomatis** (`scaledown_window=60` detik) untuk menjaga kredit komputasi gratis Modal.

---

## 1. Arsitektur Runtime Container Modal

```
apps/ai-service (AI-06: app/insight/modal_client.py)
   │  HTTPS + Authorization: Bearer <MODAL_API_KEY>
   ▼
Modal Serverless Web Endpoint (:443 -> container :8000)
   │
   ▼
auth_proxy.py (:8000)
   ├─ Validasi konstan (hmac.compare_digest) Bearer token pada /health, /v1/models, /v1/chat/completions
   ├─ Tolak tanpa/salah token (401 Unauthorized) & blokir rute non-allowlist (404 Not Found)
   └─ Sisipkan header X-Modal-Cold-Start: true/false untuk telemetri AI-06
   │
   ▼
vllm serve (127.0.0.1:8001)
   ├─ Bobot model di-cache pada Modal Volume: smart-catering-hf-cache (/root/.cache/huggingface)
   └─ Artefak kompilasi di-cache pada Modal Volume: smart-catering-vllm-cache (/root/.cache/vllm)
```

### Pemetaan File

| File                  | Fungsi                                                                                                                                                                                               |
| :-------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `config.py`           | Definisi profil deployment (`primary`, `fallback`, `fallback_awq`), validasi batas `scaledown_window` (`15..300` detik), builder argumen `vllm serve`, dan kalkulator estimasi biaya USD/detik GPU.  |
| `auth_proxy.py`       | Reverse proxy autentikasi Bearer Token (`hmac.compare_digest`) yang memproteksi seluruh rute publik (`/health`, `/v1/models`, `/v1/chat/completions`) serta menyisipkan header `X-Modal-Cold-Start`. |
| `serve_vllm.py`       | Skrip deployment Modal 1.x (`modal.App`, `modal.Image`, `modal.Volume`, `modal.Secret`, `download_weights`, dan `serve` dengan `scaledown_window=60`).                                               |
| `smoke_test.py`       | Skrip CLI pasca-deploy untuk menguji penolakan `401`, liveness `200 /health`, _cold start latency_ vs _warm latency_, validitas JSON `AI-06`, serta estimasi biaya GPU.                              |
| `test_modal_infra.py` | Unit & integration test offline (berjalan via Pytest tanpa akun Modal).                                                                                                                              |

---

## 2. Profil Model & Rencana Cadangan Hemat Kredit

| Profil (`MODAL_SLM_PROFILE`) | Model Open-Source              |  GPU Modal   |       Estimasi Tarif GPU        | Kapan Digunakan                                                               |
| :--------------------------- | :----------------------------- | :----------: | :-----------------------------: | :---------------------------------------------------------------------------- |
| **`primary`** _(default)_    | `Qwen/Qwen2.5-7B-Instruct`     | `L4` (24 GB) | ~$0.80 / jam (~$0.000222/detik) | Kualitas narasi Bahasa Indonesia & kepatuhan JSON terbaik untuk demo `AI-06`. |
| **`fallback`**               | `Qwen/Qwen2.5-3B-Instruct`     | `T4` (16 GB) | ~$0.59 / jam (~$0.000164/detik) | Cadangan ringan jika kredit menipis atau cold start 7B terlalu lambat.        |
| **`fallback_awq`**           | `Qwen/Qwen2.5-7B-Instruct-AWQ` | `T4` (16 GB) | ~$0.59 / jam (~$0.000164/detik) | Alternatif 7B terkuantisasi AWQ pada GPU T4 berbiaya rendah.                  |

> Kedua model Qwen2.5 di atas tidak bersifat _gated_ di Hugging Face sehingga tidak mewajibkan `HF_TOKEN` saat deployment (opsional jika tim kelak memilih model _gated_ seperti `meta-llama/Llama-3.2-3B-Instruct`).

---

## 3. Kontrak HTTP Eksternal (OpenAI-Compatible vLLM)

Seluruh rute yang diekspos ke publik wajib menyertakan header `Authorization: Bearer <MODAL_API_KEY>` (rute selain daftar di bawah otomatis ditolak `404 Not Found`):

| Method | Path                                                                          | Fungsi                                                            | Autentikasi                             |
| :----- | :---------------------------------------------------------------------------- | :---------------------------------------------------------------- | :-------------------------------------- |
| `POST` | `https://<workspace>--smart-catering-slm-serve.modal.run/v1/chat/completions` | Inferensi chat completions OpenAI-compatible untuk narasi `AI-06` | `Authorization: Bearer <MODAL_API_KEY>` |
| `GET`  | `https://<workspace>--smart-catering-slm-serve.modal.run/health`              | Pemeriksaan kesehatan runtime vLLM (`{"status": "healthy", ...}`) | `Authorization: Bearer <MODAL_API_KEY>` |
| `GET`  | `https://<workspace>--smart-catering-slm-serve.modal.run/v1/models`           | Daftar model aktif yang disajikan vLLM                            | `Authorization: Bearer <MODAL_API_KEY>` |

### Contoh Request & Respons

- **`GET /health` (`200 OK`):**

  ```json
  {
    "status": "healthy",
    "service": "modal-vllm",
    "model": "Qwen/Qwen2.5-7B-Instruct"
  }
  ```

- **`POST /v1/chat/completions` (`200 OK`, menyertakan header `X-Modal-Cold-Start: true|false`):**

  ```json
  {
    "model": "Qwen/Qwen2.5-7B-Instruct",
    "temperature": 0.1,
    "max_tokens": 700,
    "response_format": { "type": "json_object" },
    "messages": [
      { "role": "system", "content": "Analis operasional Catering Si Kembar..." },
      { "role": "user", "content": "<VERIFIED_KPI_DATA>...</VERIFIED_KPI_DATA>" }
    ]
  }
  ```

- **Tanpa / Salah Bearer Token (`401 Unauthorized`, header `WWW-Authenticate: Bearer`):**

  ```json
  {
    "error": {
      "message": "Unauthorized: invalid or missing Bearer token.",
      "type": "authentication_error"
    }
  }
  ```

---

## 4. Langkah Setup & Deployment ke Modal GPU

### Langkah 1 — Instalasi & Login Modal CLI

```bash
pip install modal
modal token new
```

### Langkah 2 — Buat Modal Secret (Wajib Sebelum Deploy)

Buat token acak >= 32 karakter (misal: `node -e "console.log(require('node:crypto').randomBytes(24).toString('hex'))"`), lalu daftarkan ke Modal Secrets (jangan pernah disimpan di Git):

```bash
modal secret create smart-catering-modal-secret \
  MODAL_API_KEY="<ISI_TOKEN_ACAK_MINIMAL_32_KARAKTER>"
```

_(Alias `MODAL_AUTH_TOKEN` juga didukung otomatis oleh `config.py` bila secret dibuat menggunakan nama tersebut.)_

### Langkah 3 — Pre-Warm Bobot Model ke Modal Volume (Memangkas Cold Start)

Jalankan sekali agar bobot model tersimpan permanen di Volume `smart-catering-hf-cache`:

```bash
# Untuk profil primary (Qwen2.5-7B-Instruct)
modal run infra/modal/serve_vllm.py::download_weights

# Opsional: untuk profil fallback hemat kredit (Qwen2.5-3B-Instruct)
modal run infra/modal/serve_vllm.py::download_weights --profile-name fallback
```

### Langkah 4 — Deploy Endpoint Serverless GPU

```bash
# Deploy profil primary (Qwen2.5-7B-Instruct di L4, scale-to-zero 60 detik)
modal deploy infra/modal/serve_vllm.py

# Atau deploy profil fallback hemat kredit (Qwen2.5-3B-Instruct di T4)
MODAL_SLM_PROFILE=fallback modal deploy infra/modal/serve_vllm.py
```

Setelah deploy selesai, Modal akan mencetak URL publik seperti:
`https://<workspace>--smart-catering-slm-serve.modal.run`

### Langkah 5 — Tautkan ke Root `.env` untuk `apps/ai-service` (`AI-06`)

Salin URL & token ke root `.env` (bukan `.env.example`):

```env
MODAL_SLM_BASE_URL=https://<workspace>--smart-catering-slm-serve.modal.run/v1
MODAL_API_KEY=<TOKEN_SAMA_DENGAN_MODAL_SECRET>
MODAL_SLM_MODEL=Qwen/Qwen2.5-7B-Instruct
MODAL_SLM_FALLBACK_MODEL=
MODAL_TIMEOUT_SECONDS=18
```

---

## 5. Verifikasi Endpoint, Cold Start, Scale-to-Zero & Integrasi `AI-06`

### A. Uji Offline Lokal (Tanpa Akun Modal)

Jalankan dari **root repository**:

```bash
# macOS / Linux
PYTHONPATH=. apps/ai-service/.venv/bin/pytest infra/modal/test_modal_infra.py -v

# Windows PowerShell
$env:PYTHONPATH = (Get-Location).Path
apps/ai-service/.venv/Scripts/pytest.exe infra/modal/test_modal_infra.py -v
```

### B. Smoke Test Live Pasca-Deploy (401 Auth, Cold Start & Warm Latency)

```bash
MODAL_SLM_BASE_URL="https://<workspace>--smart-catering-slm-serve.modal.run/v1" \
MODAL_API_KEY="<TOKEN_MODAL>" \
python infra/modal/smoke_test.py
```

Skrip akan memverifikasi otomatis:

1. `GET /health` tanpa token → **`401 Unauthorized`**
2. `POST /v1/chat/completions` dengan token salah → **`401 Unauthorized`**
3. `GET /health` dengan Bearer token valid → **`200 OK`**
4. 3 kali `POST /v1/chat/completions` (Request #1 mencatat `cold_start_latency_ms` + `X-Modal-Cold-Start: true`, Request #2–#3 mencatat `warm_latencies_ms` + estimasi biaya USD).

### C. Verifikasi Scale-to-Zero (Kredit Aman)

1. Tunggu > 60 detik tanpa request ke endpoint.
2. Buka Modal Dashboard → Apps → `smart-catering-slm` → pastikan jumlah container aktif turun menjadi **`0`** (status _Idle / Stopped_).

### D. Uji Integrasi Live 10 Laporan dari `apps/ai-service` (`AI-06`)

Setelah `AI-06` ter-merge ke `dev` dan `.env` terisi:

```bash
cd apps/ai-service
uv sync --extra insight --frozen
uv run --no-sync python -m app.insight.evaluation
```

---

## 6. Pemantauan Kredit, Troubleshooting & Log Pengujian Live

- **Pantau Kredit Gratis Modal ($30/bulan free tier):**
  - Dengan `L4` (~$0.80/jam) dan `scaledown_window=60` detik, 1 sesi pengujian 10 laporan (~2 menit aktif termasuk cold start + idle window) hanya memakan sekitar **~$0.03** (< 0.1% kuota gratis bulanan).
  - Cek pemakaian berkala di **Modal Dashboard → Usage & Billing** dan aktifkan _spend alert_ di batas $5–$10.
  - Jika saldo menipis atau cold start > 15 detik, segera pindah ke profil `fallback` (`T4` + `Qwen/Qwen2.5-3B-Instruct`).

### Troubleshooting Cepat

| Gejala / Error                                           | Penyebab Umum                                                                                                                | Solusi                                                                                                                                                                    |
| :------------------------------------------------------- | :--------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `401 Unauthorized`                                       | Header `Authorization: Bearer ...` kosong atau berbeda dengan `MODAL_API_KEY` di Modal Secret `smart-catering-modal-secret`. | Samakan `MODAL_API_KEY` pada root `.env` dengan Modal Secret, lalu uji ulang dengan `smoke_test.py`.                                                                      |
| `503 Service Unavailable` / timeout saat request pertama | Container sedang _cold start_ memuat bobot vLLM ke GPU.                                                                      | Pastikan `download_weights` sudah dijalankan agar bobot tersimpan di Volume `smart-catering-hf-cache`, atau naikkan `MODAL_TIMEOUT_SECONDS` (misal `20` detik) di `.env`. |
| OOM saat menjalankan model 7B di GPU `T4` (16 GB)        | Profil `primary` (7B FP16) dijalankan di GPU 16 GB.                                                                          | Gunakan GPU `L4` untuk profil `primary`, atau pindah ke `MODAL_SLM_PROFILE=fallback` (3B di `T4`) / `MODAL_SLM_PROFILE=fallback_awq` (7B AWQ di `T4`).                    |
| `ValueError: MODAL_SCALEDOWN_WINDOW`                     | Mencoba mengisi timeout idle di luar rentang `15..300` detik.                                                                | Isi nilai antara `15` hingga `300` detik (default aman: `60`).                                                                                                            |

### Template Pencatatan Hasil Uji Live (Diisi Saat Akun Modal Tim Aktif)

| Tanggal Uji                     | Profil / GPU      | Model                      | Auth 401 Check | Cold Start Latency (ms) | Avg Warm Latency (ms) | Scale-to-Zero (60s) | Estimasi Biaya Sesi (USD) |
| :------------------------------ | :---------------- | :------------------------- | :------------: | :---------------------: | :-------------------: | :-----------------: | :-----------------------: |
| _TBD (menunggu akun Modal tim)_ | `primary` / `L4`  | `Qwen/Qwen2.5-7B-Instruct` |   `[ ] PASS`   |          _TBD_          |         _TBD_         |     `[ ] PASS`      |           _TBD_           |
| _TBD (opsional cadangan)_       | `fallback` / `T4` | `Qwen/Qwen2.5-3B-Instruct` |   `[ ] PASS`   |          _TBD_          |         _TBD_         |     `[ ] PASS`      |           _TBD_           |
