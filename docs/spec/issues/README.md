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

- `area:fullstack`: Frontend Next.js, Backend Express, skema database Prisma, backend read-only tools Agentic RAG, dan antarmuka web.
- `area:ds`: Pengolahan data UMKM, EDA & definisi KPI dasbor, kamus data, dataset sintetis, dan pemodelan forecasting permintaan per menu.
- `area:ai`: Serving FastAPI, model klasifikasi relevansi dua kelas (tanpa klasifikasi intent), sentimen 2 kelas, kurasi ChromaDB, Agentic RAG dual-source tool calling, dan SLM insight.
- `area:devops`: CI/CD GitHub Actions, Docker Compose VPS, deployment Vercel, Modal GPU, dan pemeliharaan cron worker.

### Priority (Tingkat Urgensi)

- `priority:P0-blocker`: Fondasi dasar, skema arsitektur inti, atau prasyarat jalur kritis lintas tim. Harus diselesaikan pada awal milestone agar anggota lain tidak terhambat.
- `priority:P1-mvp`: Fitur utama alur bisnis katering yang wajib ada untuk demonstrasi alur end-to-end MVP.
- `priority:P2-side-quest`: Fitur pengayaan, optimasi model tambahan, otomatisasi kanal eksternal, atau nilai tambah rubrik.

### Quest Rubrik

- `quest:main`: Memenuhi kriteria checklist wajib Main Quest.
- `quest:side`: Memenuhi kriteria checklist pilihan Side Quest (nilai tambah).

---

## 4. Peta Milestone 1 Bulan (21 Nov – 20 Des 2026)

Target rilis berpedoman pada jadwal 4 minggu Project Plan A26-CS105:

```text
[M1: 21–27 Nov 2026] ──► [M2: 28 Nov–4 Des 2026] ──► [M3: 5–11 Des 2026] ──► [M4: 12–20 Des 2026]
Rancangan Disepakati     Fitur Inti Tersedia        Alur Utama Selesai &      Validasi & Finalisasi
                                                    FEATURE FREEZE (11 Des)
```

### Milestone M1: Rancangan Disepakati (21–27 Nov 2026)

Fokus: Mockup UI, kontrak API, skema DB Prisma, dataset awal & kamus data, konfigurasi ChromaDB (konfirmasi paling lambat 23 Nov 2026), baseline waktu proses, CI, dan uji kelayakan layanan.

- `FS-01`: App Mockup, Desain Responsif & App Shell Staf Senior (`P0-blocker`, `quest:main`, `quest:side`)
- `FS-02`: Skema Database Prisma, Migrasi & Seed Data Uji (`P0-blocker`, `quest:main`, `quest:side`)
- `FS-03`: Autentikasi, RBAC & Standar Validasi Express `/api/v1` (Joi) (`P0-blocker`, `quest:main`, `quest:side`)
- `DS-01`: Pengumpulan, Anonimisasi & Data Wrangling Data UMKM (`P0-blocker`, `quest:main`)
- `DS-03`: Kamus Data, Generator Data Sintetik (`is_synthetic`) & Paket Dataset untuk Gen AI (`P0-blocker`, `quest:main`, `quest:side`)
- `AI-01`: Dokumentasi Masalah AI, Kontrak OpenAPI & Kerangka Serving FastAPI (`P0-blocker`, `quest:main`, `quest:side`) — _(Selesai / CLOSED)_
- `AI-04`: Kurasi Knowledge Base Tervalidasi PIC & Retrieval ChromaDB (`P1-mvp`, `quest:main`, `quest:side`)
- `OPS-01`: Tata Kelola Git/PR, GitHub Actions CI & Secrets Hygiene (`P0-blocker`, `quest:main`, `quest:side`)

### Milestone M2: Fitur Inti Tersedia (28 Nov – 4 Des 2026)

Fokus: Input pesanan (validasi harga DB) & invoice awal, katalog menu/resep & konversi satuan bahan, EDA 5 pertanyaan & **penguncian definisi KPI dasbor**, model relevansi 2 kelas, forecasting per menu (evaluasi objektif MA vs RF), model sentimen, pipeline Agentic RAG dasar, Docker Compose VPS, deployment Vercel, dan penyiapan inference Modal GPU.

- `FS-04`: Modul Katalog Menu, Resep & Kalkulator Bahan Otomatis (`P1-mvp`, `quest:main`)
- `FS-05`: Modul Pesanan & Dasbor Jadwal Produksi (`P1-mvp`, `quest:main`)
- `DS-02`: EDA 5 Pertanyaan Bisnis, Definisi KPI Dasbor, Visualisasi & Rekomendasi Operasional (`P1-mvp`, `quest:main`, `quest:side`)
- `DS-04`: Feature Engineering & Modeling Forecasting Permintaan per Menu (Moving Average vs Random Forest) (`P2-side-quest`, `quest:side`)
- `AI-02`: Model Utama Latih Sendiri: Klasifikasi Relevansi Dua Kelas (`P1-mvp`, `quest:main`)
- `AI-03`: Model Tambahan: Klasifikasi Sentimen Feedback Pelanggan (`P2-side-quest`, `quest:side`)
- `AI-05`: Pipeline Agentic RAG, Dual-Source Tool Calling, Prompt Terstruktur & Guardrail (`P1-mvp`, `quest:main`, `quest:side`)
- `OPS-02`: Docker Compose Produksi & Provisioning VPS + Reverse Proxy HTTPS (`P1-mvp`, `quest:main`, `quest:side`)
- `OPS-03`: Deployment Frontend Vercel & Verifikasi Koneksi BFF Desktop/Mobile (`P1-mvp`, `quest:main`, `quest:side`)
- `OPS-04`: Deployment SLM/LLM Open-Source di Modal GPU (vLLM) (`P2-side-quest`, `quest:side`)

### Milestone M3: Alur Utama Selesai & Feature Freeze (5–11 Des 2026)

Fokus: Alur utama tuntas (pencatatan DP minimal 60% `[Menunggu Konfirmasi PIC]`, pelunasan, konfirmasi pesanan, PDF Invoice), integrasi Chat AI + backend read-only tools DB, Dasbor Analitik + estimasi bahan forecasting + PDF Laporan Analitik, serving forecasting per menu, AI Business Insight, kanal WhatsApp WAHA, kode fitur reminder & konfigurasi cron VPS, serta **Feature Freeze pada 11 Des 2026**.

- `FS-06`: Modul Keuangan: Invoice Digital, DP 60%, Pelunasan & PDF Invoice (`P1-mvp`, `quest:main`)
- `FS-07`: Modul Chat AI: Proxy Backend, Read-Only Tools DB, Riwayat Chat & UI Web (`P1-mvp`, `quest:main`, `quest:side`)
- `FS-08`: Modul Dasbor Analitik DS: KPI, Filter, Upload Data, Estimasi Bahan Forecasting & PDF Laporan (`P2-side-quest`, `quest:side`)
- `DS-05`: Integrasi Pipeline Inferensi Forecasting per Menu ke `apps/ai-service` (`P2-side-quest`, `quest:side`)
- `AI-06`: Modul AI Business Insight (SLM/LLM Open-Source & Evaluasi 10 Laporan) (`P2-side-quest`, `quest:side`)
- `AI-07`: Integrasi Kanal WhatsApp (WAHA / Cloud API Test) & Uji Resiliensi Layanan AI (`P2-side-quest`, `quest:side`)

### Milestone M4: Validasi & Finalisasi (12–20 Des 2026)

Fokus _(pasca Feature Freeze — hanya pengujian, perbaikan bug, dan dokumentasi)_: Pengujian sistem end-to-end (20 skenario Project Plan), uji cron ganda tanpa duplikasi & failover pra-demo, verifikasi implementasi KPI & audit akurasi data akhir, demonstrasi skenario **100 nasi box** & pengukuran waktu sistem vs baseline manual bersama PIC UMKM, serta finalisasi README dan user manual.

- `FS-09`: Modul Pengingat Otomatis (In-App, WAHA, Email), User Manual, Ukur Waktu Proses & Uji E2E (`P1-mvp`, `quest:main`, `quest:side`) _(kode fitur reminder selesai ≤ akhir M3 / Feature Freeze)_
- `DS-06`: Verifikasi Implementasi KPI Dasbor & Audit Akurasi Data Akhir (`P1-mvp`, `quest:main`, `quest:side`)
- `OPS-05`: Penjadwalan Cron Worker VPS, Backup DB/Chroma & Uji Failover Pra-Demo (`P2-side-quest`, `quest:side`) _(konfigurasi cron VPS selesai ≤ akhir M3 / Feature Freeze)_

---

## 5. Tabel Indeks 27 Issue

| ID       | Judul Issue                                                                                      | Area             | Priority                 | Quest                      | Milestone                | Berkas Spesifikasi                           |
| :------- | :----------------------------------------------------------------------------------------------- | :--------------- | :----------------------- | :------------------------- | :----------------------- | :------------------------------------------- |
| `FS-01`  | App Mockup, Desain Responsif & App Shell Staf Senior                                             | `area:fullstack` | `priority:P0-blocker`    | `quest:main`, `quest:side` | `M1 (21–27 Nov 2026)`    | [01-fullstack.md](01-fullstack.md)           |
| `FS-02`  | Skema Database Prisma, Migrasi & Seed Data Uji                                                   | `area:fullstack` | `priority:P0-blocker`    | `quest:main`, `quest:side` | `M1 (21–27 Nov 2026)`    | [01-fullstack.md](01-fullstack.md)           |
| `FS-03`  | Autentikasi, RBAC & Standar Validasi Express `/api/v1` (Joi)                                     | `area:fullstack` | `priority:P0-blocker`    | `quest:main`, `quest:side` | `M1 (21–27 Nov 2026)`    | [01-fullstack.md](01-fullstack.md)           |
| `FS-04`  | Modul Katalog Menu, Resep & Kalkulator Bahan Otomatis                                            | `area:fullstack` | `priority:P1-mvp`        | `quest:main`               | `M2 (28 Nov–4 Des 2026)` | [01-fullstack.md](01-fullstack.md)           |
| `FS-05`  | Modul Pesanan & Dasbor Jadwal Produksi                                                           | `area:fullstack` | `priority:P1-mvp`        | `quest:main`               | `M2 (28 Nov–4 Des 2026)` | [01-fullstack.md](01-fullstack.md)           |
| `FS-06`  | Modul Keuangan: Invoice Digital, DP 60%, Pelunasan & PDF Invoice                                 | `area:fullstack` | `priority:P1-mvp`        | `quest:main`               | `M3 (5–11 Des 2026)`     | [01-fullstack.md](01-fullstack.md)           |
| `FS-07`  | Modul Chat AI: Proxy Backend, Read-Only Tools DB, Riwayat Chat & UI Web                          | `area:fullstack` | `priority:P1-mvp`        | `quest:main`, `quest:side` | `M3 (5–11 Des 2026)`     | [01-fullstack.md](01-fullstack.md)           |
| `FS-08`  | Modul Dasbor Analitik DS: KPI, Filter, Upload Data, Estimasi Bahan Forecasting & PDF Laporan     | `area:fullstack` | `priority:P2-side-quest` | `quest:side`               | `M3 (5–11 Des 2026)`     | [01-fullstack.md](01-fullstack.md)           |
| `FS-09`  | Modul Pengingat Otomatis (In-App, WAHA, Email), User Manual, Ukur Waktu Proses & Uji E2E         | `area:fullstack` | `priority:P1-mvp`        | `quest:main`, `quest:side` | `M4 (12–20 Des 2026)`    | [01-fullstack.md](01-fullstack.md)           |
| `DS-01`  | Pengumpulan, Anonimisasi & Data Wrangling Data UMKM                                              | `area:ds`        | `priority:P0-blocker`    | `quest:main`               | `M1 (21–27 Nov 2026)`    | [02-data-science.md](02-data-science.md)     |
| `DS-02`  | EDA 5 Pertanyaan Bisnis, Definisi KPI Dasbor, Visualisasi & Rekomendasi Operasional              | `area:ds`        | `priority:P1-mvp`        | `quest:main`, `quest:side` | `M2 (28 Nov–4 Des 2026)` | [02-data-science.md](02-data-science.md)     |
| `DS-03`  | Kamus Data, Generator Data Sintetik (`is_synthetic`) & Paket Dataset untuk Gen AI                | `area:ds`        | `priority:P0-blocker`    | `quest:main`, `quest:side` | `M1 (21–27 Nov 2026)`    | [02-data-science.md](02-data-science.md)     |
| `DS-04`  | Feature Engineering & Modeling Forecasting Permintaan per Menu (Moving Average vs Random Forest) | `area:ds`        | `priority:P2-side-quest` | `quest:side`               | `M2 (28 Nov–4 Des 2026)` | [02-data-science.md](02-data-science.md)     |
| `DS-05`  | Integrasi Pipeline Inferensi Forecasting per Menu ke `apps/ai-service`                           | `area:ds`        | `priority:P2-side-quest` | `quest:side`               | `M3 (5–11 Des 2026)`     | [02-data-science.md](02-data-science.md)     |
| `DS-06`  | Verifikasi Implementasi KPI Dasbor & Audit Akurasi Data Akhir                                    | `area:ds`        | `priority:P1-mvp`        | `quest:main`, `quest:side` | `M4 (12–20 Des 2026)`    | [02-data-science.md](02-data-science.md)     |
| `AI-01`  | Dokumentasi Masalah AI, Kontrak OpenAPI & Kerangka Serving FastAPI                               | `area:ai`        | `priority:P0-blocker`    | `quest:main`, `quest:side` | `M1 (21–27 Nov 2026)`    | [03-ai-engineering.md](03-ai-engineering.md) |
| `AI-02`  | Model Utama Latih Sendiri: Klasifikasi Relevansi Dua Kelas                                       | `area:ai`        | `priority:P1-mvp`        | `quest:main`               | `M2 (28 Nov–4 Des 2026)` | [03-ai-engineering.md](03-ai-engineering.md) |
| `AI-03`  | Model Tambahan: Klasifikasi Sentimen Feedback Pelanggan                                          | `area:ai`        | `priority:P2-side-quest` | `quest:side`               | `M2 (28 Nov–4 Des 2026)` | [03-ai-engineering.md](03-ai-engineering.md) |
| `AI-04`  | Kurasi Knowledge Base Tervalidasi PIC & Retrieval ChromaDB                                       | `area:ai`        | `priority:P1-mvp`        | `quest:main`, `quest:side` | `M1 (21–27 Nov 2026)`    | [03-ai-engineering.md](03-ai-engineering.md) |
| `AI-05`  | Pipeline Agentic RAG, Dual-Source Tool Calling, Prompt Terstruktur & Guardrail                   | `area:ai`        | `priority:P1-mvp`        | `quest:main`, `quest:side` | `M2 (28 Nov–4 Des 2026)` | [03-ai-engineering.md](03-ai-engineering.md) |
| `AI-06`  | Modul AI Business Insight (SLM/LLM Open-Source & Evaluasi 10 Laporan)                            | `area:ai`        | `priority:P2-side-quest` | `quest:side`               | `M3 (5–11 Des 2026)`     | [03-ai-engineering.md](03-ai-engineering.md) |
| `AI-07`  | Integrasi Kanal WhatsApp (WAHA / Cloud API Test) & Uji Resiliensi Layanan AI                     | `area:ai`        | `priority:P2-side-quest` | `quest:side`               | `M3 (5–11 Des 2026)`     | [03-ai-engineering.md](03-ai-engineering.md) |
| `OPS-01` | Tata Kelola Git/PR, GitHub Actions CI & Secrets Hygiene                                          | `area:devops`    | `priority:P0-blocker`    | `quest:main`, `quest:side` | `M1 (21–27 Nov 2026)`    | [04-devops-infra.md](04-devops-infra.md)     |
| `OPS-02` | Docker Compose Produksi & Provisioning VPS + Reverse Proxy HTTPS                                 | `area:devops`    | `priority:P1-mvp`        | `quest:main`, `quest:side` | `M2 (28 Nov–4 Des 2026)` | [04-devops-infra.md](04-devops-infra.md)     |
| `OPS-03` | Deployment Frontend Vercel & Verifikasi Koneksi BFF Desktop/Mobile                               | `area:devops`    | `priority:P1-mvp`        | `quest:main`, `quest:side` | `M2 (28 Nov–4 Des 2026)` | [04-devops-infra.md](04-devops-infra.md)     |
| `OPS-04` | Deployment SLM/LLM Open-Source di Modal GPU (vLLM)                                               | `area:devops`    | `priority:P2-side-quest` | `quest:side`               | `M2 (28 Nov–4 Des 2026)` | [04-devops-infra.md](04-devops-infra.md)     |
| `OPS-05` | Penjadwalan Cron Worker VPS, Backup DB/Chroma & Uji Failover Pra-Demo                            | `area:devops`    | `priority:P2-side-quest` | `quest:side`               | `M4 (12–20 Des 2026)`    | [04-devops-infra.md](04-devops-infra.md)     |

---

## 6. Matriks Dependensi Lintas Area

```text
[Jalur Transaksi Utama]
FS-01 (Mockup/Shell) ──► FS-02 (Prisma Schema) ──► FS-03 (Auth/Joi) ──► FS-04 (Menus, Resep & Satuan) ──► FS-05 (Pesanan DB Price & Jadwal) ──► FS-06 (Invoice, DP 60%, Pelunasan & PDF Invoice) ──► FS-09 (E2E 100 Box & Ukur Waktu)

[Jalur Data Science ke AI & Web]
DS-01 (Wrangling) ──► DS-03 (Data Synth/Kamus) ──┬──► AI-02 (Relevansi 2 Kelas) ─────────────────────────┐
                                                 └──► AI-03 (Sentimen 2 Kelas) ──────────────────────────┼──► FS-08 (Dasbor Analitik, Estimasi Bahan & PDF Laporan) ──► DS-06 (Verifikasi KPI & Audit Akhir)
DS-01 (Wrangling) ──► DS-02 (EDA & Kunci KPI M2) ────────────────────────────────────────────────────────┤
DS-01 (Wrangling) ──► DS-04 (Forecasting per Menu: MA vs RF) ──► DS-05 (Serving Forecasting per Menu) ───┘

[Jalur Agentic RAG Dual-Source & SLM Insight]
AI-01 (FastAPI) ──┬──► AI-04 (ChromaDB KB + 4 Metadata) ──┬──► AI-05 (Agentic RAG Dual-Source) ──┬──► FS-07 (Proxy Chat + Read-Only Tools DB + UI)
FS-05/FS-06 ──────┴──► FS-07 (/internal/agent-tools/*) ───┘                                      └──► AI-07 (WhatsApp WAHA + Resiliensi)
OPS-04 (Modal GPU M2) ──► AI-06 (SLM Business Insight JSON) ──► FS-08 (PDF Laporan Analitik)

[Jalur Otomasi & Deployment]
OPS-01 (CI Actions) ──► OPS-02 (VPS Compose) ──► OPS-03 (Vercel BFF) ──► FS-09 (Uji Responsif & E2E)
FS-04/FS-05/FS-06 ────► AI-07 (WAHA) ──────────► FS-09 (4 Jenis Reminder ≤ M3) ──► OPS-05 (Cron VPS ≤ M3 & Uji Failover M4)
```

### Penjelasan Titik Kritis:

1. **Pondasi Data (`DS-01` & `DS-03`):** AI Engineering membutuhkan dataset teks berlabel dari Data Science untuk melatih model relevansi 2 kelas (`AI-02`) dan sentimen 2 kelas (`AI-03`). Jika data riil belum mencukupi pada minggu pertama, `DS-03` menyediakan paket data sintetis berpenanda `is_synthetic = true` dengan persetujuan PIC.
2. **Penguncian Definisi KPI Sebelum Dasbor (`DS-02` → `FS-08` → `DS-06`):** Formula matematis KPI bisnis dikunci di `DS-02` (M2) sebelum diimplementasikan di `FS-08` (M3), lalu diverifikasi kecocokan 100%-nya di `DS-06` (M4).
3. **Agentic RAG Dual-Source Tanpa SQL Bebas (`AI-04`, `AI-05`, `FS-07`):** Frontend Next.js hanya berkomunikasi dengan Express `/api/v1/chat/*`. FastAPI `/api/v1/rag/chat` menyaring pesan melalui model relevansi 2 kelas (`AI-02`), lalu agen LLM memilih tools ke dua sumber: (1) ChromaDB (`AI-04`) untuk menu/FAQ/SOP/aturan pembayaran tervalidasi PIC beserta 4 metadata, dan (2) backend read-only tools Express (`/api/v1/internal/agent-tools/*` di `FS-07`) untuk pesanan, invoice, status DP, pelunasan, dan jadwal aktual dengan penegakan RBAC di backend Express (**dilarang akses SQL bebas kepada LLM**).
4. **Pembagian Tanggung Jawab PDF & Forecasting per Menu (`FS-04`, `FS-06`, `DS-04/05`, `AI-06`, `FS-08`):** `FS-06` khusus merender **PDF Invoice Pesanan**; `FS-08` khusus merender **PDF Laporan Analitik + AI Business Insight** (memakai narasi JSON dari `AI-06`) sekaligus menggabungkan proyeksi **forecasting per menu** (`DS-05`) dengan resep standar (`FS-04`) untuk menampilkan estimasi kebutuhan bahan baku.

---

## 7. Daftar Item yang Menunggu Konfirmasi

Untuk menjaga integritas spesifikasi dan menghindari asumsi sepihak, item-item berikut ditandai secara transparan dan memerlukan konfirmasi resmi:

### Menunggu Konfirmasi PIC UMKM (`[Menunggu Konfirmasi PIC]`)

1. **Aturan Uang Muka (DP) Minimal 60%:** Kepastian persentase minimum DP dan apakah DP di bawah batas ditolak mutlak atau diizinkan dengan peringatan/catatan khusus Admin.
2. **Formula Baku Resep, Harga Resmi & Pembulatan Bahan:** Rincian gramatur bahan per porsi, harga resmi menu nasi box, serta apakah daftar belanja cukup menampilkan hasil presisi konversi (`gram ↔ kg`, `ml ↔ liter`) atau perlu saran pembulatan kemasan.
3. **Penyediaan Rekap Riwayat Transaksi & Persetujuan Data Sintetis:** Ekspor rekap Spreadsheet pesanan teranonimisasi (tanpa PII & data gaji) serta persetujuan penggunaan data sintetis berlabel `is_synthetic = true` sebagai cadangan simulasi.
4. **Validasi Konten Knowledge Base (`menus.md`, `faq.md`, `sop.md`, `payment_policy.md`):** Konfirmasi status `verified` beserta tanggal dan versi dokumen.
5. **Batas Visibilitas Status Pembayaran untuk `STAFF`:** Apakah staf operasional boleh melihat label status bayar ringkas di dasbor jadwal atau chatbot tanpa nominal uang, atau seluruh informasi invoice khusus `ADMIN`.
6. **Nomor WhatsApp Cadangan & Whitelist Staf WAHA:** Izin penggunaan nomor sekunder (bukan nomor utama UMKM) untuk pairing QR WAHA sebagai prototype dan daftar nomor staf terdaftar.
7. **Baseline Waktu Manual & Jadwal Demonstrasi 100 Nasi Box:** Pencatatan waktu manual hitung bahan & invoice (M1), format resmi PDF Invoice, serta jadwal demo & final survey (M4).

### Perlu Konfirmasi Tim Capstone (`[Perlu Konfirmasi Tim]`)

1. **Visibilitas Repositori GitHub (`OPS-01`):** Penyelarasan status repositori saat ini (`PUBLIC`) terhadap ketentuan Project Plan (_"Repository wajib private"_).
2. **Kontrak Lintas Layanan Express ↔ FastAPI:** Finalisasi skema JSON `/api/v1/internal/agent-tools/*`, transport sesi BFF (`HttpOnly cookie` vs `Authorization: Bearer`), batas timeout LLM/Modal (15–20 detik), dan minimal hari historis forecasting (`>= 7` hari).
3. **Definisi Matematis KPI (`DS-02`):** Kesepakatan final definisi omzet/revenue (`Order CONFIRMED` vs `Payment` masuk) dan format template CSV/XLSX unggahan `FS-08`.
4. **Penyedia Layanan & Model Teknis:** Pilihan API LLM proprietary (Gemini vs OpenAI), model embedding (lokal multilingual vs API), bobot SLM Modal GPU (`Qwen2.5-7B-Instruct` vs `Llama-3.2-3B`/kuantisasi), akun/domain VPS & Vercel, pustaka PDF (`pdfkit`) & grafik (`Recharts`), serta kanal email opsional (SendGrid/SMTP).

---

## 8. Guardrail Wajib (Tindakan yang Dilarang)

Seluruh anggota tim dan pengembang wajib mematuhi batasan mutlak berikut dalam setiap pengerjaan issue:

### Larangan Full-Stack

- ❌ **Dilarang menampilkan fitur utama yang belum berfungsi:** Tidak boleh membiarkan tombol mati tanpa aksi, navigasi buntu, atau halaman berlabel "segera hadir" pada alur utama yang diujikan.
- ❌ **Dilarang memercayai harga dari input client:** Harga satuan dan total tagihan pesanan wajib divalidasi langsung dari database backend `Menu`.
- ❌ **Dilarang membocorkan rahasia atau PII:** Tidak boleh menulis atau mengekspos token, password, API key, `DATABASE_URL`, data gaji, atau identitas pelanggan nyata di kode, repositori, maupun log.

### Larangan AI Engineering / Gen AI

- ❌ **Dilarang memberikan akses SQL bebas (`text-to-SQL`) atau tools mutasi data kepada LLM:** Akses database oleh Agentic RAG wajib melalui backend read-only tools Express tervalidasi Joi dengan penegakan RBAC di backend.
- ❌ **Dilarang menggunakan model TensorFlow Hub siap pakai, API LLM proprietary sebagai pengganti model latih sendiri, maupun AutoML** untuk model klasifikasi relevansi 2 kelas (`AI-02`).
- ❌ **Dilarang mengganti chatbot RAG memakai SLM insight (`AI-06`)** saat API LLM mengalami gangguan/kuota habis.
- ❌ **Dilarang melakukan forking liar:** Tidak boleh menyalin repositori aplikasi luar tanpa izin atau atribusi sah.

### Larangan Data Science

- ❌ **Dilarang menggunakan data tanpa menjelaskan asal-usulnya atau menyamarkan data sintetis sebagai data riil:** Seluruh data buatan wajib memiliki penanda `is_synthetic = true` dan penjelasan metode pembuatannya di README.
- ❌ **Dilarang memanipulasi data atau hasil evaluasi:** Perbandingan Moving Average vs Random Forest wajib objektif pada split kronologis tanpa kebocoran data (_data leakage_).
- ❌ **Dilarang membuat klaim dampak bisnis tanpa bukti:** Penghematan waktu proses dilaporkan sebagai hasil teramati demonstrasi (target `< 5 menit` hanya potensi).

### Batasan Arsitektur Monorepo

- ❌ Dilarang Frontend Next.js memanggil database PostgreSQL atau AI Service FastAPI `:8001` secara langsung.
- ❌ Dilarang Worker Node.js mengimpor kode internal `apps/api` maupun `apps/ai-service`.
- ❌ Dilarang memodifikasi kontrak wire REST di luar spesifikasi envelope `{ data, meta }` dan standar error RFC 9457 `application/problem+json`.
