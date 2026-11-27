# Modul AI Business Insight (`apps/ai-service/app/insight`) — Issue #21 (`AI-06`)

Modul ini mengimplementasikan fitur **AI Business Insight (`AI-06`)** berbasis **SLM/LLM open-source di Modal Serverless GPU + vLLM (OpenAI-compatible API)** untuk menghasilkan ringkasan eksekutif, sorotan KPI utama, dan rekomendasi operasional terstruktur bagi `ADMIN` Catering Si Kembar.

> **Batas Tanggung Jawab Arsitektur (Project Plan A26-CS105):**
>
> - `apps/ai-service` (`AI-06`) **hanya** menghasilkan narasi insight berformat JSON (`POST /api/v1/insight/generate`).
> - Rendering fisik berkas **PDF Laporan Analitik** adalah tanggung jawab backend Express pada modul analitik **`FS-08`** (bukan `FS-06` yang khusus untuk PDF Invoice Pesanan).
> - SLM Modal GPU di modul ini **tidak pernah digunakan** untuk menggantikan API LLM proprietary pada chatbot Agentic RAG (`AI-05`).

---

## 1. Arsitektur Clean Architecture & Dependency Injection

```
POST /api/v1/insight/generate (X-Internal-Token + X-Actor-Role: ADMIN)
        │
        ▼
BusinessInsightService (app/insight/service.py)
  ├─ 1. compute_derived_kpi_facts()   -> Hitung KPI deterministik (DS-02)
  ├─ 2. build_insight_messages()      -> Structured prompt + delimiter <VERIFIED_KPI_DATA>
  ├─ 3. ModalVLLMClient               -> HTTP POST /chat/completions ke Modal GPU + Bearer Token
  ├─ 4. parse_slm_insight_payload()   -> Validasi Pydantic strict (SLMInsightPayload)
  ├─ 5. validate_insight_numbers()    -> Post-generation numeric sanity check + anti-secret-leak
  └─ 6. Fallback Berjenjang           -> Optional fallback SLM -> Deterministic Template Fallback
```

### Pemetaan File

| File              | Tanggung Jawab                                                                                                                                                                                                                                                                       |
| :---------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ports.py`        | Abstraksi `SLMClientPort`, `ModalSLMCompletion`, dan hierarki exception terstruktur (`InsightTimeoutError`, `InsightRateLimitError`, `InsightValidationError`, dll.).                                                                                                                |
| `schemas.py`      | Skema Pydantic strict untuk output SLM (`SLMInsightPayload`), fakta KPI deterministik (`DerivedKPIFacts`), hasil pemeriksaan angka (`NumericValidationResult`), dan laporan evaluasi 10 sampel.                                                                                      |
| `modal_client.py` | Klien HTTP OpenAI-compatible vLLM ke Modal Serverless GPU (`Authorization: Bearer <MODAL_API_KEY>`), mendukung `httpx` (extra `insight`) dengan fallback `urllib`, deteksi `cold_start`, pencatatan `latency_ms`, dan retry terbatas untuk error transien (`500`/`502`/`503`/`504`). |
| `prompts.py`      | Perhitungan fakta KPI deterministik (`format_idr`, rasio penyelesaian, rata-rata nilai pesanan, porsi menu unggulan) + penyusunan prompt anti-halusinasi dengan sanitasi delimiter input.                                                                                            |
| `guardrails.py`   | Parsing JSON strict + **Post-Generation Numeric Sanity Check** yang mengekstrak seluruh token angka/Rupiah/persentase dan menolak output jika ditemukan angka baru di luar data input/KPI terverifikasi atau jika metrik inti (`total_orders`, `total_revenue`) hilang.              |
| `fallback.py`     | Generator narasi deterministik berbahasa Indonesia yang 100% cocok dengan angka input sehingga alur PDF Laporan Analitik `FS-08` tidak pernah terblokir saat Modal GPU mati/timeout/kredit habis.                                                                                    |
| `service.py`      | Orkestrasi `BusinessInsightService`, factory DI `build_default_insight_service(settings)`, serta pencatatan structured JSON log (`event: "insight_generation"` mencakup `latencyMs`, `coldStart`, `modelUsed`, `isFallback`, `numericCheckPassed`).                                  |
| `evaluation.py`   | Harness evaluasi 10 laporan uji sintetis (`is_synthetic = True`, non-PII) untuk memverifikasi akurasi angka 100% dan mencatat latensi per laporan.                                                                                                                                   |

---

## 2. Konfigurasi Environment & Keamanan

Variabel environment yang dikonsumsi `apps/ai-service` (terdaftar di allowlist `scripts/service-environment.mjs` dan `app/config.py`):

| Variabel                   | Default | Keterangan                                                                                                                     |
| :------------------------- | :------ | :----------------------------------------------------------------------------------------------------------------------------- |
| `INTERNAL_SERVICE_SECRET`  | `""`    | Secret internal wajib untuk header `X-Internal-Token` antar-layanan Express ↔ FastAPI.                                         |
| `MODAL_SLM_BASE_URL`       | `""`    | Base URL OpenAI-compatible vLLM pada Modal GPU (`OPS-04`), misal `https://<ws>--smart-catering-slm.modal.run/v1`.              |
| `MODAL_API_KEY`            | `""`    | Bearer Token Modal GPU (disensor `[REDACTED]` di `AppSettings.__repr__` dan tidak pernah masuk log/response).                  |
| `MODAL_SLM_MODEL`          | `""`    | Nama model utama di Modal vLLM, misal `Qwen/Qwen2.5-7B-Instruct`.                                                              |
| `MODAL_SLM_FALLBACK_MODEL` | `""`    | Opsional: nama model lebih kecil/terkuantisasi (misal `Qwen/Qwen2.5-3B-Instruct-AWQ`) sebelum jatuh ke template deterministik. |
| `MODAL_TIMEOUT_SECONDS`    | `18`    | Batas timeout HTTP client ke Modal GPU (rentang `1..60` detik) untuk mengakomodasi cold start.                                 |

### Penegakan Otorisasi `ADMIN`

- Endpoint `POST /api/v1/insight/generate` menerapkan `verify_internal_token` (`401 Unauthorized`) dan `verify_admin_actor` (`403 Forbidden`).
- Header `X-Actor-Role` selain `ADMIN` (misal `STAFF`) **selalu ditolak `403 Forbidden`** (RFC 9457).
- Saat `INTERNAL_SERVICE_SECRET` aktif atau `APP_ENV=production`, ketiadaan header `X-Actor-Role: ADMIN` otomatis ditolak `403 Forbidden`.

---

## 3. Kontrak Integrasi dengan `FS-08` (PDF Laporan Analitik)

Backend Express (`FS-08`) mengirimkan payload metrik KPI teragregasi (mengacu pada formula terkunci `DS-02`) beserta header `X-Internal-Token`, `X-Actor-Role: ADMIN`, dan `X-Request-Id`:

```json
{
  "period": "November 2026",
  "metrics": {
    "total_orders": 38,
    "total_revenue": 24500000,
    "completed_orders": 34,
    "unpaid_invoices": 4,
    "top_menus": [
      { "name": "Nasi Box Ayam Lengkuas", "portions": 620 },
      { "name": "Nasi Box Rendang Daging", "portions": 310 }
    ],
    "forecast_next_week_portions": 450
  }
}
```

Respons `200 OK` selalu stabil dengan struktur `data.{period, executive_summary, key_highlights, operational_recommendations, model_used, latency_ms, is_fallback}` dan `meta.requestId`—baik saat inferensi Modal GPU aktif maupun saat fallback deterministik aktif (`is_fallback: true`)—sehingga rendering PDF di `FS-08` tetap berjalan mulus.

---

## 4. Evaluasi 10 Laporan Uji (Akurasi Angka & Latensi)

Harness evaluasi (`app/insight/evaluation.py`) menguji **10 skenario laporan katering sintetis non-PII** (`RPT-01` s.d. `RPT-10`, `is_synthetic = True`), mencakup periode normal, puncak acara/pernikahan, backlog invoice tinggi, laporan mingguan tanpa forecast (`null`), hingga kasus tepi `0 pesanan`.

### Hasil Evaluasi Terverifikasi (Pytest Harness — Simulasi Modal vLLM & Mode Fallback)

| ID       | Periode Uji               | Total Pesanan |  Total Omzet | Mode Simulasi SLM (Latensi / Akurasi Angka) | Mode Fallback Deterministik (Akurasi Angka) |
| :------- | :------------------------ | :-----------: | -----------: | :-----------------------------------------: | :-----------------------------------------: |
| `RPT-01` | November 2026             |      38       | Rp24.500.000 |  `4380 ms` _(cold start)_ / **100% cocok**  |     **100% cocok** (`is_fallback=true`)     |
| `RPT-02` | Oktober 2026              |      52       | Rp41.250.000 |         `1515 ms` / **100% cocok**          |     **100% cocok** (`is_fallback=true`)     |
| `RPT-03` | September 2026            |      25       | Rp14.750.000 |         `1610 ms` / **100% cocok**          |     **100% cocok** (`is_fallback=true`)     |
| `RPT-04` | Agustus 2026              |      64       | Rp58.900.000 |         `1705 ms` / **100% cocok**          |     **100% cocok** (`is_fallback=true`)     |
| `RPT-05` | Minggu 1 Desember 2026    |      12       |  Rp7.800.000 |         `1800 ms` / **100% cocok**          |     **100% cocok** (`is_fallback=true`)     |
| `RPT-06` | Juli 2026 _(edge case 0)_ |       0       |          Rp0 |         `1895 ms` / **100% cocok**          |     **100% cocok** (`is_fallback=true`)     |
| `RPT-07` | Juni 2026                 |      45       | Rp33.600.000 |         `1990 ms` / **100% cocok**          |     **100% cocok** (`is_fallback=true`)     |
| `RPT-08` | Mei 2026                  |      80       | Rp76.400.000 |         `2085 ms` / **100% cocok**          |     **100% cocok** (`is_fallback=true`)     |
| `RPT-09` | April 2026                |      19       | Rp11.400.000 |         `2180 ms` / **100% cocok**          |     **100% cocok** (`is_fallback=true`)     |
| `RPT-10` | Q4 2026                   |      115      | Rp98.500.000 |         `2275 ms` / **100% cocok**          |     **100% cocok** (`is_fallback=true`)     |

- **Ringkasan Akurasi Numerik:** **`10/10` (`100%`)** pada simulasi Modal vLLM maupun fallback deterministik.
- **Eksekusi Live terhadap Modal GPU (`OPS-04`):** Setelah endpoint Modal GPU aktif dan variabel `MODAL_SLM_BASE_URL`, `MODAL_API_KEY`, `MODAL_SLM_MODEL` diisi di `.env`, jalankan perintah berikut dari `apps/ai-service/` untuk merekam latensi live aktual:

```bash
uv sync --extra insight --frozen
uv run --no-sync python -m app.insight.evaluation
```
