# Indeks Spesifikasi Teknis 27 Issue (`docs/spec/issues`)

Dokumen ini merupakan master indeks dan pedoman implementasi teknis untuk 27 issue kerja proyek Smart Catering (Catering Si Kembar) bagi tim Full-Stack, Data Science, AI Engineering, dan DevOps/Infra. Seluruh spesifikasi disusun selaras dengan Project Plan A26-CS105, rubrik pembelajaran Main Quest dan Side Quest, serta arsitektur monorepo aktual.

---

## 1. Acuan Arsitektur Monorepo Aktual

Sistem dikembangkan menggunakan arsitektur monorepo terisolasi dengan boundary domain yang tegas:

- `apps/web`: Next.js App Router + TypeScript + Tailwind CSS + shadcn/ui. Menggunakan BFF Axios internal (`/api/*`) yang meneruskan permintaan ke `API_BASE_URL` secara server-side. Boundary: Dilarang mengimpor koneksi database/secret server dan dilarang menghubungi `apps/ai-service` secara langsung dari client browser.
- `apps/api`: Express 5.3.0 + TypeScript + Joi 18.3.2 + Prisma (`packages/db`) dengan base route `/api/v1/*`. Memiliki modul bisnis transaksional (`auth`, `menus`, `orders`, `finance`, `analytics`, `chat`, `reminders`) dan integrasi backend (`waha`, `email`). Wire contract konsisten: response sukses `{ "data": ..., "meta": { "requestId": "..." } }`, response error RFC 9457 `application/problem+json`, header korelasi `X-Request-Id`, dokumentasi OpenAPI 3.1.0 + Scalar fail-closed di produksi.
- `apps/ai-service`: Python 3.12 (`uv`) + FastAPI + Pydantic + Uvicorn (port internal VPS `:8001`). Menangani pipeline machine learning, kurasi ChromaDB, agentic RAG, sentimen, forecasting, dan insight bisnis dengan envelope dan penanganan error RFC 9457 seragam.
- `apps/worker`: Node.js TypeScript daemon independen (port liveness internal `:3002`). Dijalankan via cron sistem VPS untuk pengingat jadwal produksi dan pembayaran tanpa Redis/BullMQ pada fase MVP. Boundary: Dilarang mengimpor internal code `apps/api` maupun `apps/ai-service`.
- `packages/db`: Prisma Client dan skema PostgreSQL 17.
- `packages/types`: Shared TypeScript interfaces dan wire contracts.
- `data/`: Ruang kerja data (`data/raw`, `data/synthetic`, `data/knowledge`, `data/dictionary`).
- `infra/`: Pengelolaan container dan orkestrasi Docker (`infra/docker`) serta serverless GPU (`infra/modal`).

---

## 2. Standar Kontrak API & Dokumentasi OpenAPI (Scalar)

Seluruh layanan backend (`apps/api` Express dan `apps/ai-service` FastAPI) wajib mematuhi standar kontrak API, struktur envelope, penanganan kesalahan, dan dokumentasi interaktif yang seragam di seluruh monorepo.

### 2.1 Pola URL, Routing & Base Path

- **Backend Transaksional (`apps/api`):** Seluruh rute bisnis menggunakan prefix `/api/v1/*` (misal: `/api/v1/auth`, `/api/v1/menus`, `/api/v1/orders`, `/api/v1/finance`, `/api/v1/chat`, `/api/v1/analytics`, `/api/v1/reminders`). Rute liveness/readiness tersedia di `GET /health` dan `GET /api/v1/health` dengan response `{"status":"ok"}`.
- **Layanan AI & Forecasting (`apps/ai-service`):** Berjalan di port internal VPS `:8001` dengan base path `/api/v1/*` (misal: `/api/v1/rag/chat`, `/api/v1/ml/forecast/demand`, `/api/v1/insight/generate`). Layanan ini berada di jaringan privat VPS dan tidak boleh diakses langsung oleh browser publik.
- **Frontend BFF (`apps/web`):** Menggunakan Next.js App Router Route Handlers di `/api/*` yang meneruskan panggilan ke `apps/api` secara server-side.

### 2.2 Wire Contract Response Sukses

Setiap response sukses wajib dibungkus dalam envelope JSON standar:

```json
{
  "data": {
    "id": "ord_01",
    "orderNumber": "ORD-202612-0001",
    "totalAmount": 2500000
  },
  "meta": {
    "requestId": "0192f0c8-7b3a-7000-8000-000000000001"
  }
}
```

Untuk endpoint daftar/koleksi (_list_), objek `meta` wajib menyertakan blok `pagination`:

```json
{
  "data": [{ "id": "menu_01", "name": "Nasi Box Ayam Lengkuas", "price": 25000 }],
  "meta": {
    "requestId": "0192f0c8-7b3a-7000-8000-000000000002",
    "pagination": {
      "page": 1,
      "limit": 10,
      "total": 42,
      "totalPages": 5
    }
  }
}
```

Header response wajib menyertakan:

- `X-Request-Id: <uuid>` (selaras dengan `meta.requestId`).
- `Content-Type: application/json; charset=utf-8`.
- Operasi mutasi tanpa isi pengembalian (misal: pembatalan atau soft-delete) mengembalikan status `204 No Content` tanpa body.

### 2.3 Wire Contract Penanganan Kesalahan (RFC 9457)

Seluruh kesalahan wajib menggunakan format standar RFC 9457 `application/problem+json`:

```json
{
  "type": "https://datatracker.ietf.org/doc/html/rfc9457",
  "title": "Unprocessable Content",
  "status": 422,
  "detail": "Validasi payload request gagal.",
  "instance": "/api/v1/orders",
  "requestId": "0192f0c8-7b3a-7000-8000-000000000003",
  "errors": [
    {
      "path": "items.0.portion",
      "code": "number.min",
      "message": "Porsi minimal pemesanan adalah 1"
    }
  ]
}
```

Daftar kode status HTTP yang digunakan:

- `200 OK`: Permintaan berhasil dan mengembalikan data.
- `201 Created`: Entitas baru berhasil dibuat.
- `204 No Content`: Aksi berhasil dieksekusi tanpa body pengembalian.
- `400 Bad Request`: Format payload salah secara sintaksis (misal: JSON malformed).
- `401 Unauthorized`: Kredensial autentikasi tidak ada, kedaluwarsa, atau tidak valid.
- `403 Forbidden`: Pengguna terautentikasi tetapi tidak memiliki hak akses yang memadai.
- `404 Not Found`: Sumber daya yang diminta tidak ditemukan di database.
- `409 Conflict`: Terjadi konflik status bisnis (misal: invoice sudah lunas, pesanan sudah terkirim).
- `422 Unprocessable Content`: Validasi skema Joi atau Pydantic gagal.
- `500 Internal Server Error`: Kesalahan server internal yang tidak tertangani.
- `503 Service Unavailable`: Layanan hilir tidak tersedia atau batas waktu tercapai (misal: AI Service timeout).

### 2.4 Standar Role, RBAC & Status Enum Lintas Modul

- **Role Pengguna:**
  - `ADMIN`: Pemilik / Pengelola Katering. Memiliki hak penuh atas konfigurasi menu, transaksi pesanan, keuangan, invoice, analitik, dan manajemen akun staf.
  - `STAFF`: Staf Operasional / Dapur. Memiliki akses ke jadwal produksi, daftar pesanan, resep bahan baku, kalkulator kebutuhan bahan, dan asisten chat AI. Dilarang mengakses modul keuangan (`/api/v1/finance/*`), analitik sensitif, dan manajemen pengguna internal.
  - Penambahan role tambahan: `[Perlu Konfirmasi Tim]`.
  - Mekanisme transport sesi (`HttpOnly cookie` lewat BFF vs `Authorization: Bearer`): `[Perlu Konfirmasi Tim]`.
- **Enum Status Pesanan (`OrderStatus`):**
  - `DRAFT`: Pesanan baru dibuat, belum dikonfirmasi.
  - `CONFIRMED`: Pesanan telah dikonfirmasi dan pembayaran DP valid.
  - `IN_PREPARATION`: Pesanan sedang disiapkan di dapur.
  - `READY`: Pesanan selesai dimasak dan siap dikirim/diambil.
  - `DELIVERED`: Pesanan telah diterima pemesan.
  - `CANCELLED`: Pesanan dibatalkan.
- **Enum Status Pembayaran (`PaymentStatus`):**
  - `UNPAID`: Belum ada pembayaran tercatat.
  - `PARTIALLY_PAID`: Pembayaran uang muka (DP minimal 60% `[Menunggu Konfirmasi PIC]`) telah diterima, sisa tagihan belum lunas.
  - `PAID`: Seluruh tagihan invoice telah lunas 100%.

### 2.5 Dokumentasi OpenAPI 3.1.0 & Scalar UI (`/docs`)

- Setiap endpoint Express wajib terdaftar pada skema OpenAPI 3.1.0 yang diekspos di `GET /api/openapi`.
- Setiap endpoint FastAPI `apps/ai-service` wajib terdaftar pada skema OpenAPI 3.1.0 di `GET /openapi.json`.
- Dokumentasi interaktif disajikan menggunakan **Scalar** (`@scalar/api-reference`) pada rute `GET /docs`.
- **Kebijakan Fail-Closed di Produksi:**
  - Ketersediaan Scalar UI dikontrol secara ketat oleh variabel lingkungan `DOCS_ENABLED`.
  - Pada lingkungan produksi, `DOCS_ENABLED` default bernilai `false` (mengembalikan HTTP `404 Not Found`).
  - Jika diaktifkan secara selektif untuk pengujian staging/mitra, wajib diproteksi oleh HTTP Basic Auth dengan kredensial minimal 32 karakter di balik enkripsi TLS/HTTPS.

---

## 3. Skema Label Issue Tracker

Setiap issue memiliki label metadata standar untuk pelacakan dan filter di issue tracker:

### Area (Disiplin Kerja)

- `area:fullstack`: Frontend Next.js, Backend Express, skema database Prisma, dan antarmuka web.
- `area:ds`: Pengolahan data UMKM, EDA, kamus data, dataset sintetis, dan pemodelan forecasting.
- `area:ai`: Serving FastAPI, model klasifikasi relevansi/intent, sentimen, kurasi ChromaDB, RAG, dan SLM insight.
- `area:devops`: CI/CD GitHub Actions, Docker Compose VPS, deployment Vercel, Modal GPU, dan pemeliharaan worker.

### Priority (Tingkat Urgensi)

- `priority:P0-blocker`: Fondasi dasar, skema arsitektur inti, atau prasyarat jalur kritis lintas tim. Harus diselesaikan pada awal milestone agar anggota lain tidak terhambat.
- `priority:P1-mvp`: Fitur utama alur bisnis katering yang wajib ada untuk demonstrasi alur end-to-end MVP.
- `priority:P2-side-quest`: Fitur pengayaan, optimasi model tambahan, otomatisasi kanal eksternal, atau nilai tambah rubrik.

### Quest Rubrik

- `quest:main`: Memenuhi kriteria checklist wajib Main Quest.
- `quest:side`: Memenuhi kriteria checklist pilihan Side Quest (nilai tambah).

---

## 4. Peta Milestone 1 Bulan (21 Nov – 20 Des 2026)

Target rilis berpedoman pada jadwal 4 minggu proyek:

```text
[M1: 21–27 Nov 2026] ──► [M2: 28 Nov–4 Des 2026] ──► [M3: 5–11 Des 2026] ──► [M4: 12–20 Des 2026]
Rancangan Disepakati     Fitur Inti Tersedia        Alur Utama Selesai &      Validasi & Finalisasi
                                                    FEATURE FREEZE (11 Des)
```

### Milestone M1: Rancangan Disepakati (21–27 Nov 2026)

Fokus: Mockup antarmuka, baseline manual, kontrak API, skema DB, kamus data, dataset awal, konfigurasi ChromaDB, CI, dan uji kelayakan layanan pihak ketiga.

- `FS-01`: App Mockup, Desain Responsif & App Shell Staf Senior (`P0-blocker`, `quest:main`, `quest:side`)
- `FS-02`: Skema Database Prisma, Migrasi & Seed Data Uji (`P0-blocker`, `quest:main`, `quest:side`)
- `FS-03`: Autentikasi, RBAC & Standar Validasi Express `/api/v1` (Joi) (`P0-blocker`, `quest:main`, `quest:side`)
- `DS-01`: Pengumpulan, Anonimasi & Data Wrangling Data UMKM (`P0-blocker`, `quest:main`)
- `DS-03`: Kamus Data, Generator Data Sintetik (`is_synthetic`) & Paket Dataset untuk Gen AI (`P0-blocker`, `quest:main`, `quest:side`)
- `AI-01`: Dokumentasi Masalah AI, Kontrak OpenAPI & Kerangka Serving FastAPI (`P0-blocker`, `quest:main`, `quest:side`)
- `AI-04`: Kurasi Knowledge Base Tervalidasi PIC & Retrieval ChromaDB (`P1-mvp`, `quest:side`)
- `OPS-01`: Tata Kelola Git/PR, GitHub Actions CI & Secrets Hygiene (`P0-blocker`, `quest:main`, `quest:side`)

### Milestone M2: Fitur Inti Tersedia (28 Nov – 4 Des 2026)

Fokus: Input pesanan, katalog menu/resep, perhitungan bahan, model relevansi, forecasting baseline vs RF, model sentimen, pipeline RAG, Docker Compose VPS, dan deployment Vercel.

- `FS-04`: Modul Katalog Menu, Resep & Kalkulator Bahan Otomatis (`P1-mvp`, `quest:main`)
- `FS-05`: Modul Pesanan & Dasbor Jadwal Produksi (`P1-mvp`, `quest:main`)
- `DS-02`: EDA 5 Pertanyaan Bisnis, Visualisasi & Rekomendasi Operasional (`P1-mvp`, `quest:main`)
- `DS-04`: Feature Engineering & Modeling Forecasting Permintaan (`P2-side-quest`, `quest:side`)
- `AI-02`: Model Utama Latih Sendiri: Klasifikasi Relevansi / Intent (`P1-mvp`, `quest:main`, `quest:side`)
- `AI-03`: Model Tambahan: Klasifikasi Sentimen Feedback Pelanggan (`P2-side-quest`, `quest:side`)
- `AI-05`: Pipeline Agentic RAG, Tool Calling, Prompt Terstruktur & Guardrail (`P1-mvp`, `quest:main`, `quest:side`)
- `OPS-02`: Docker Compose Produksi & Provisioning VPS + Reverse Proxy HTTPS (`P1-mvp`, `quest:main`, `quest:side`)
- `OPS-03`: Deployment Frontend Vercel & Verifikasi Koneksi BFF Desktop/Mobile (`P1-mvp`, `quest:main`, `quest:side`)

### Milestone M3: Alur Utama Selesai & Feature Freeze (5–11 Des 2026)

Fokus: Pencatatan DP dan pelunasan invoice, export PDF, integrasi chat AI dan dasbor analitik di UI, serving forecasting di AI service, inference SLM Modal GPU, uji kanal WAHA, dan **Feature Freeze pada 11 Des 2026**.

- `FS-06`: Modul Keuangan: Invoice Digital, DP 60%, Pelunasan & Export PDF (`P1-mvp`, `quest:main`)
- `FS-07`: Modul Chat AI: Proxy Backend, Riwayat Inferensi DB & UI Chat (`P2-side-quest`, `quest:side`)
- `FS-08`: Modul Dasbor Analitik DS: KPI, Filter, Upload Data & Tampilan Prediksi/Insight (`P2-side-quest`, `quest:side`)
- `DS-05`: Integrasi Pipeline Inferensi Forecasting ke `apps/ai-service` (`P2-side-quest`, `quest:side`)
- `AI-06`: Modul AI Business Insight (SLM/LLM Open-Source & Evaluasi 10 Laporan) (`P2-side-quest`, `quest:side`)
- `AI-07`: Integrasi Kanal WhatsApp (WAHA / Cloud API Test) & Uji Resiliensi Layanan AI (`P2-side-quest`, `quest:side`)
- `OPS-04`: Deployment SLM/LLM Open-Source di Modal GPU (vLLM) (`P2-side-quest`, `quest:side`)

### Milestone M4: Validasi & Finalisasi (12–20 Des 2026)

Fokus: Pengujian sistem end-to-end, simulasi skenario 100 nasi box bersama PIC UMKM, pengukuran waktu sistem vs baseline manual, cron worker pengingat, audit data akhir, penyusunan README dan manual pengguna.

- `FS-09`: Modul Pengingat (In-App + Email Worker), Panduan Pengguna, Ukur Waktu Proses & Uji E2E (`P1-mvp`, `quest:main`, `quest:side`)
- `DS-06`: Spesifikasi KPI Dasbor Bisnis & Audit Akurasi Data Akhir (`P1-mvp`, `quest:main`, `quest:side`)
- `OPS-05`: Penjadwalan Cron Worker VPS, Backup DB/Chroma & Uji Failover Pra-Demo (`P2-side-quest`, `quest:side`)

---

## 5. Tabel Indeks 27 Issue

| ID       | Judul Issue                                                                             | Area             | Priority                 | Quest                      | Milestone                | Berkas Spesifikasi                           |
| :------- | :-------------------------------------------------------------------------------------- | :--------------- | :----------------------- | :------------------------- | :----------------------- | :------------------------------------------- |
| `FS-01`  | App Mockup, Desain Responsif & App Shell Staf Senior                                    | `area:fullstack` | `priority:P0-blocker`    | `quest:main`, `quest:side` | `M1 (21–27 Nov 2026)`    | [01-fullstack.md](01-fullstack.md)           |
| `FS-02`  | Skema Database Prisma, Migrasi & Seed Data Uji                                          | `area:fullstack` | `priority:P0-blocker`    | `quest:main`, `quest:side` | `M1 (21–27 Nov 2026)`    | [01-fullstack.md](01-fullstack.md)           |
| `FS-03`  | Autentikasi, RBAC & Standar Validasi Express `/api/v1` (Joi)                            | `area:fullstack` | `priority:P0-blocker`    | `quest:main`, `quest:side` | `M1 (21–27 Nov 2026)`    | [01-fullstack.md](01-fullstack.md)           |
| `FS-04`  | Modul Katalog Menu, Resep & Kalkulator Bahan Otomatis                                   | `area:fullstack` | `priority:P1-mvp`        | `quest:main`               | `M2 (28 Nov–4 Des 2026)` | [01-fullstack.md](01-fullstack.md)           |
| `FS-05`  | Modul Pesanan & Dasbor Jadwal Produksi                                                  | `area:fullstack` | `priority:P1-mvp`        | `quest:main`               | `M2 (28 Nov–4 Des 2026)` | [01-fullstack.md](01-fullstack.md)           |
| `FS-06`  | Modul Keuangan: Invoice Digital, DP 60%, Pelunasan & Export PDF                         | `area:fullstack` | `priority:P1-mvp`        | `quest:main`               | `M3 (5–11 Des 2026)`     | [01-fullstack.md](01-fullstack.md)           |
| `FS-07`  | Modul Chat AI: Proxy Backend, Riwayat Inferensi DB & UI Chat                            | `area:fullstack` | `priority:P2-side-quest` | `quest:side`               | `M3 (5–11 Des 2026)`     | [01-fullstack.md](01-fullstack.md)           |
| `FS-08`  | Modul Dasbor Analitik DS: KPI, Filter, Upload Data & Tampilan Prediksi/Insight          | `area:fullstack` | `priority:P2-side-quest` | `quest:side`               | `M3 (5–11 Des 2026)`     | [01-fullstack.md](01-fullstack.md)           |
| `FS-09`  | Modul Pengingat (In-App + Email Worker), Panduan Pengguna, Ukur Waktu Proses & Uji E2E  | `area:fullstack` | `priority:P1-mvp`        | `quest:main`, `quest:side` | `M4 (12–20 Des 2026)`    | [01-fullstack.md](01-fullstack.md)           |
| `DS-01`  | Pengumpulan, Anonimasi & Data Wrangling Data UMKM                                       | `area:ds`        | `priority:P0-blocker`    | `quest:main`               | `M1 (21–27 Nov 2026)`    | [02-data-science.md](02-data-science.md)     |
| `DS-02`  | EDA 5 Pertanyaan Bisnis, Visualisasi & Rekomendasi Operasional                          | `area:ds`        | `priority:P1-mvp`        | `quest:main`               | `M2 (28 Nov–4 Des 2026)` | [02-data-science.md](02-data-science.md)     |
| `DS-03`  | Kamus Data, Generator Data Sintetik (`is_synthetic`) & Paket Dataset untuk Gen AI       | `area:ds`        | `priority:P0-blocker`    | `quest:main`, `quest:side` | `M1 (21–27 Nov 2026)`    | [02-data-science.md](02-data-science.md)     |
| `DS-04`  | Feature Engineering & Modeling Forecasting Permintaan (Moving Average vs Random Forest) | `area:ds`        | `priority:P2-side-quest` | `quest:side`               | `M2 (28 Nov–4 Des 2026)` | [02-data-science.md](02-data-science.md)     |
| `DS-05`  | Integrasi Pipeline Inferensi Forecasting ke `apps/ai-service`                           | `area:ds`        | `priority:P2-side-quest` | `quest:side`               | `M3 (5–11 Des 2026)`     | [02-data-science.md](02-data-science.md)     |
| `DS-06`  | Spesifikasi KPI Dasbor Bisnis & Audit Akurasi Data Akhir                                | `area:ds`        | `priority:P1-mvp`        | `quest:main`, `quest:side` | `M4 (12–20 Des 2026)`    | [02-data-science.md](02-data-science.md)     |
| `AI-01`  | Dokumentasi Masalah AI, Kontrak OpenAPI & Kerangka Serving FastAPI                      | `area:ai`        | `priority:P0-blocker`    | `quest:main`, `quest:side` | `M1 (21–27 Nov 2026)`    | [03-ai-engineering.md](03-ai-engineering.md) |
| `AI-02`  | Model Utama Latih Sendiri: Klasifikasi Relevansi / Intent                               | `area:ai`        | `priority:P1-mvp`        | `quest:main`, `quest:side` | `M2 (28 Nov–4 Des 2026)` | [03-ai-engineering.md](03-ai-engineering.md) |
| `AI-03`  | Model Tambahan: Klasifikasi Sentimen Feedback Pelanggan                                 | `area:ai`        | `priority:P2-side-quest` | `quest:side`               | `M2 (28 Nov–4 Des 2026)` | [03-ai-engineering.md](03-ai-engineering.md) |
| `AI-04`  | Kurasi Knowledge Base Tervalidasi PIC & Retrieval ChromaDB                              | `area:ai`        | `priority:P1-mvp`        | `quest:side`               | `M1 (21–27 Nov 2026)`    | [03-ai-engineering.md](03-ai-engineering.md) |
| `AI-05`  | Pipeline Agentic RAG, Tool Calling, Prompt Terstruktur & Guardrail                      | `area:ai`        | `priority:P1-mvp`        | `quest:main`, `quest:side` | `M2 (28 Nov–4 Des 2026)` | [03-ai-engineering.md](03-ai-engineering.md) |
| `AI-06`  | Modul AI Business Insight (SLM/LLM Open-Source & Evaluasi 10 Laporan)                   | `area:ai`        | `priority:P2-side-quest` | `quest:side`               | `M3 (5–11 Des 2026)`     | [03-ai-engineering.md](03-ai-engineering.md) |
| `AI-07`  | Integrasi Kanal WhatsApp (WAHA / Cloud API Test) & Uji Resiliensi Layanan AI            | `area:ai`        | `priority:P2-side-quest` | `quest:side`               | `M3 (5–11 Des 2026)`     | [03-ai-engineering.md](03-ai-engineering.md) |
| `OPS-01` | Tata Kelola Git/PR, GitHub Actions CI & Secrets Hygiene                                 | `area:devops`    | `priority:P0-blocker`    | `quest:main`, `quest:side` | `M1 (21–27 Nov 2026)`    | [04-devops-infra.md](04-devops-infra.md)     |
| `OPS-02` | Docker Compose Produksi & Provisioning VPS + Reverse Proxy HTTPS                        | `area:devops`    | `priority:P1-mvp`        | `quest:main`, `quest:side` | `M2 (28 Nov–4 Des 2026)` | [04-devops-infra.md](04-devops-infra.md)     |
| `OPS-03` | Deployment Frontend Vercel & Verifikasi Koneksi BFF Desktop/Mobile                      | `area:devops`    | `priority:P1-mvp`        | `quest:main`, `quest:side` | `M2 (28 Nov–4 Des 2026)` | [04-devops-infra.md](04-devops-infra.md)     |
| `OPS-04` | Deployment SLM/LLM Open-Source di Modal GPU (vLLM)                                      | `area:devops`    | `priority:P2-side-quest` | `quest:side`               | `M3 (5–11 Des 2026)`     | [04-devops-infra.md](04-devops-infra.md)     |
| `OPS-05` | Penjadwalan Cron Worker VPS, Backup DB/Chroma & Uji Failover Pra-Demo                   | `area:devops`    | `priority:P2-side-quest` | `quest:side`               | `M4 (12–20 Des 2026)`    | [04-devops-infra.md](04-devops-infra.md)     |

---

## 6. Matriks Dependensi Lintas Area

```text
[Jalur Transaksi Utama]
FS-01 (Mockup/Shell) ──► FS-02 (Prisma Schema) ──► FS-03 (Auth/Joi) ──► FS-04 (Menus & Resep) ──► FS-05 (Pesanan) ──► FS-06 (Keuangan/DP) ──► FS-09 (E2E & Demo)

[Jalur Data Science ke AI & Web]
DS-01 (Wrangling) ──► DS-03 (Data Synth/Kamus) ──┬──► AI-02 (Model Relevansi/Intent) ──┐
                                                 └──► AI-03 (Model Sentimen) ──────────┼──► AI-05 (Agentic RAG) ──► FS-07 (Chat UI & Proxy)
DS-01 (Wrangling) ──► DS-02 (EDA 5 Masalah)                                            │
DS-01 (Wrangling) ──► DS-04 (Forecasting RF) ───────► DS-05 (Serving AI Service) ──────┴──► FS-08 (Dasbor Analitik) ──► DS-06 (Audit KPI)

[Jalur Knowledge Base & AI Serving]
AI-01 (FastAPI Frame) ──┬──► AI-04 (ChromaDB KB) ──► AI-05 (Agentic RAG) ──► AI-07 (WAHA / WhatsApp)
                        └──► OPS-04 (Modal GPU SLM) ──► AI-06 (Insight Report PDF) ──► FS-08 (Unduh PDF)

[Jalur Otomasi & Deployment]
OPS-01 (CI Actions) ──► OPS-02 (VPS Compose) ──► OPS-03 (Vercel BFF) ──► FS-09 (Pengujian Responsif & E2E)
FS-05/FS-06 ──────────► AI-07 (WAHA) ─────────► FS-09 (Reminder In-App & Email) ──► OPS-05 (VPS Cron & Uji Failover)
```

### Penjelasan Titik Kritis:

1. **Pondasi Data (`DS-01` & `DS-03`):** AI Engineering membutuhkan dataset teks berlabel dari Data Science untuk melatih model relevansi (`AI-02`) dan model sentimen (`AI-03`). Jika data riil belum mencukupi pada minggu pertama, `DS-03` wajib menyediakan paket data sintetis berpenanda `is_synthetic = true`.
2. **Pondasi Database & Kontrak (`FS-02` & `FS-03`):** Seluruh modul bisnis web bergantung pada tersedianya tabel relasional Prisma dan endpoint Express yang tervalidasi skema Joi.
3. **Penyajian AI ke Frontend (`AI-01`, `AI-05`, `FS-07`):** Frontend Next.js tidak boleh mengakses FastAPI `:8001` secara langsung. Endpoint Express `/api/v1/chat/messages` bertindak sebagai reverse proxy/BFF yang memvalidasi otentikasi pengguna, meneruskan prompt ke FastAPI `POST /api/v1/rag/chat`, menyimpan riwayat ke database PostgreSQL, dan mengembalikan respons ke client.
4. **Alur Peramalan & Analitik (`DS-04`, `DS-05`, `FS-08`):** Data Science mengembangkan model runtun waktu di notebook, lalu mempaketkannya ke format serialisasi standar (`joblib`) di `apps/ai-service/app/ml/forecasting/artifacts/forecasting_rf.joblib`. FastAPI melayani inferensi via `POST /api/v1/ml/forecast/demand`. Express kemudian mengambil hasil estimasi dan menampilkannya pada grafik dasbor analitik.

---

## 7. Daftar Item yang Menunggu Konfirmasi

Untuk menjaga integritas spesifikasi dan menghindari asumsi sepihak, item-item berikut ditandai secara transparan dan memerlukan konfirmasi resmi:

### Menunggu Konfirmasi PIC UMKM (`[Menunggu Konfirmasi PIC]`)

1. **Aturan Uang Muka (DP) Minimal 60%:** Diperlukan penegasan apakah batas minimum 60% bersifat kaku (_hard block_) atau dapat disesuaikan pada pesanan khusus pelanggan langganan.
2. **Formula Baku Resep dan Takaran Bahan:** Rincian takaran gramatur bumbu, protein, beras, dan sayuran per porsi box sesuai daftar menu resmi UMKM agar perhitungan kalkulator bahan baku akurat.
3. **Harga Jual Menu dan Paket Nasi Box:** Daftar harga resmi terbaru untuk perhitungan invoice digital otomatis.
4. **Penyediaan Rekap Riwayat Transaksi:** Ekspor rekap pesanan masa lalu (Spreadsheet) untuk dianonimkan sebagai data latih dan evaluasi model forecasting.
5. **Nomor WhatsApp Cadangan dan Izin WAHA:** Penyediaan satu nomor telepon sekunder UMKM khusus untuk pemasangan sesi QR WAHA agar nomor bisnis utama UMKM terhindar dari risiko pembatasan akun (_banned_).
6. **Batas Kapasitas Maksimal Produksi Harian:** Batasan jumlah porsi maksimal yang dapat dimasak dapur per hari sebelum pesanan ditolak atau diberi tanda peringatan kapasitas.

### Perlu Konfirmasi Tim Capstone (`[Perlu Konfirmasi Tim]`)

1. **Klasifikasi 2 Kelas Relevansi (Wajib Project Plan) vs >= 4 Kelas Intent (Opsional):** Model utama `AI-02` ditetapkan menggunakan **2 kelas relevansi** (`relevant` vs `out_of_domain`) dipadukan dengan Agentic RAG tool calling sesuai Project Plan. Ekstensi menjadi klasifikasi intent >= 4 kelas (misal: `tanya_produk`, `pemesanan`, `keluhan`, `lainnya`) bersifat **opsional** sebagai nilai tambah Side Quest apabila masih tersedia waktu sebelum feature freeze (`11 Des 2026`).
2. **Penyedia Layanan Proprietary LLM API:** Pemilihan provider model generatif (Google Gemini API vs OpenAI API) berdasarkan ketersediaan kuota gratis dan latensi respons.
3. **Kredensial Layanan Email Transaksional:** Penentuan akun SMTP/SendGrid gratis untuk kebutuhan notifikasi email pengingat pada background worker.
4. **Batas Split Kronologis Forecasting:** Penetapan batas tanggal _holdout split_ (misal 80% data awal untuk training, 20% data akhir untuk testing) agar simulasi evaluasi MAE/RMSE/WAPE tidak mengalami kebocoran data (_data leakage_).
5. **Mekanisme Transport Sesi Autentikasi:** Pemilihan antara `HttpOnly cookie` lewat BFF Next.js vs header `Authorization: Bearer <token>` untuk kemudahan pengujian API klien dan keamanan browser.
6. **SLA Batas Waktu Respon Asisten AI:** Penentuan batas waktu timeout inferensi (default 10 detik) sebelum backend beralih ke fallback graceful message.

---

## 8. Guardrail Wajib (Tindakan yang Dilarang)

Seluruh anggota tim dan pengembang wajib mematuhi batasan mutlak berikut dalam setiap pengerjaan issue:

### Larangan Full-Stack

- ❌ **Dilarang menampilkan fitur utama yang belum berfungsi:** Tidak boleh membiarkan tombol mati tanpa aksi, navigasi buntu, atau halaman berlabel "segera hadir" pada alur utama yang diujikan.
- ❌ **Dilarang membocorkan rahasia:** Tidak boleh menulis atau mengekspos token, password, API key, `DATABASE_URL`, atau credential di client-side code, repositori git publik, maupun log.
- ❌ **Dilarang menggunakan data pribadi pelanggan nyata tanpa izin:** Seluruh nama pelanggan, alamat spesifik, nomor HP, dan nominal pribadi wajib disamarkan atau dianonimkan.

### Larangan AI Engineering / Gen AI

- ❌ **Dilarang menggunakan model TensorFlow Hub siap pakai sebagai model utama Main Quest:** Model klasifikasi utama wajib dilatih sendiri dari dataset yang diproses tim Data Science.
- ❌ **Dilarang menggunakan API LLM proprietary secara langsung sebagai pengganti model AI latih sendiri:** Fitur utama klasifikasi relevansi tidak boleh digantikan oleh prompt wrapper LLM komersial.
- ❌ **Dilarang menggunakan AutoML:** Seluruh proses modeling, feature extraction, dan evaluasi wajib dikodekan secara eksplisit.
- ❌ **Dilarang melakukan forking liar:** Tidak boleh menyalin atau mengklon repositori aplikasi luar tanpa izin atau atribusi sah.

### Larangan Data Science

- ❌ **Dilarang menggunakan data tanpa menjelaskan asal-usulnya:** Setiap dataset wajib memiliki dokumentasi sumber, metodologi pengumpulan, atau skrip generatornya.
- ❌ **Dilarang menyamarkan data sintetis sebagai data riil:** Data sintetis atau augmentasi wajib memiliki flag penanda eksplisit `is_synthetic = true`.
- ❌ **Dilarang memanipulasi data untuk mengarahkan hasil:** Tidak boleh mengubah atau membuang data historis secara sepihak untuk memperbagus akurasi model.
- ❌ **Dilarang membuat klaim dampak bisnis yang tidak didukung data:** Penghematan waktu proses operasional wajib dilaporkan sebagai hasil pengujian teramati pada demonstrasi, bukan klaim dampak komersial definitif.

### Batasan Arsitektur Monorepo

- ❌ Dilarang Frontend Next.js memanggil database PostgreSQL atau AI Service FastAPI `:8001` secara langsung.
- ❌ Dilarang Worker Node.js mengimpor kode internal `apps/api` maupun `apps/ai-service`.
- ❌ Dilarang memodifikasi kontrak wire REST di luar spesifikasi envelope `{ data, meta }` dan standar error RFC 9457 `application/problem+json`.
