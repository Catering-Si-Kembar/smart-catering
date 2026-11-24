# Product Requirements Document (PRD) — Smart Catering

**Versi:** 3.1 · **Diperbarui:** 2026-11-24 · **ID Tim:** A26-CS105 · **Mitra UMKM:** Catering Si Kembar  
**Program:** Capstone Project Asah 2026 led by Dicoding supported by GoTo  
**Repository:** [Catering-Si-Kembar/smart-catering](https://github.com/Catering-Si-Kembar/smart-catering) · **Project Board:** [GitHub Project #1](https://github.com/orgs/Catering-Si-Kembar/projects/1)

---

## 1. Kedudukan Dokumen & Status Proyek

Dokumen ini adalah **dokumen konteks dan persyaratan produk terpadu (Master PRD)** untuk pengembangan **Smart Catering** bagi mitra **Catering Si Kembar**. PRD ini menyatukan:

- Cakupan bisnis, jadwal 1 bulan (`M1`–`M4`), manajemen risiko, dan 20 skenario pengujian dari [Project Plan A26-CS105](Asah_2026_Project_Plan_A26-CS105.md).
- Arsitektur aktual **Hybrid Minimal Monorepo** enam workspace setelah migrasi backend ke **Express 5.3.0 + TypeScript + Joi 18.3.2 + `/api/v1`** ([ADR-0005](decisions/0005-express-joi-api-v1.md)), penataan ruang kerja tim, dan penyiapan frontend **Next.js + Tailwind CSS + shadcn/ui + Axios BFF**.
- Pemetaan operasional ke **27 Technical Issue Specification** lintas 4 area di [docs/spec/issues/README.md](spec/issues/README.md).

Dokumen [PRD Fase 0 (v2.2)](PRD_FASE_0.md) dipertahankan sebagai catatan historis fondasi awal, sementara seluruh pengembangan fitur MVP (Fase 1, `M1`–`M4`) mengacu pada dokumen ini.

> **Status aktual:** Fondasi arsitektur monorepo, migrasi Express + Joi `/api/v1`, struktur ruang kerja tim, paket 27 spesifikasi teknis issue, dan tata kelola PR/CI sudah disiapkan. Seluruh fitur bisnis operasional, pipeline ML/RAG/forecasting, dan deployment produksi merupakan cakupan implementasi fase `M1`–`M4` dan **belum diklaim selesai** hingga lulus pengujian terukur.

---

## 2. Latar Belakang Masalah, Tujuan & Pengguna Sasaran

### 2.1 Kondisi Operasional Sebelum Solusi

Catering Si Kembar (bidang Food & Beverage / F&B) mengelola pesanan harian dan acara (seperti paket nasi box) secara manual:

- Perhitungan kebutuhan bahan baku dilakukan manual per pesanan, rawan salah hitung dan menyita waktu saat volume besar (misal 100 nasi box).
- Pencatatan keuangan dilakukan di buku fisik sehingga penerbitan invoice memakan waktu beberapa jam hingga keesokan harinya.
- Pemantauan jadwal pesanan berada di Google Spreadsheet terpisah; staf operasional (terutama staf senior yang kurang terbiasa dengan aplikasi digital) sering harus bertanya berulang kali kepada pengelola.
- Respons pertanyaan berulang melalui WhatsApp terasa lambat karena belum ada basis pengetahuan dan asisten pencarian informasi yang terstruktur.

### 2.2 Tujuan Produk

Membangun **prototype/MVP aplikasi web manajemen katering** yang mudah digunakan di desktop dan ponsel, mencakup:

1. **Alur inti operasional wajib (Main Quest):** pencatatan pesanan, perhitungan kebutuhan bahan baku otomatis dari resep standar, penerbitan invoice digital + pencatatan DP dan pelunasan, serta dasbor jadwal produksi yang ramah staf senior.
2. **Pengayaan berbasis Data Science & Gen AI (Side Quest):** pengolahan & analisis 5 pertanyaan bisnis, chatbot Agentic RAG (web & WhatsApp WAHA terbatas), model klasifikasi relevansi latih sendiri, analisis sentimen pelanggan, forecasting permintaan menu, dasbor analitik interaktif + unggah data, AI Business Insight berbasis SLM/LLM open-source dengan unduhan PDF, serta pengingat otomatis anti-duplikasi.

> **Batas klaim:** Hasil capstone adalah prototype untuk demonstrasi dan validasi bersama PIC UMKM (termasuk uji skenario 100 nasi box pada Minggu 4). Penghematan waktu proses dilaporkan sebagai **hasil teramati saat demonstrasi** (target invoice `< 5 menit` disebut sebagai potensi, bukan klaim dampak bisnis komersial), dan mitra tidak diwajibkan mengadopsi sistem ke operasional penuh.

### 2.3 Pengguna Sasaran & Peran (RBAC)

| Peran (`Role`) | Profil Pengguna                | Hak Akses & Kebutuhan Utama                                                                                                                                                         |
| -------------- | ------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ADMIN`        | Pemilik / Pengelola Katering   | Akses penuh: kelola akun staf, katalog menu & resep, pesanan, modul keuangan (`/api/v1/finance/*`), dasbor analitik & upload data, AI Insight PDF.                                  |
| `STAFF`        | Staf Operasional & Staf Senior | Akses baca/input pesanan, kalkulator bahan baku, dasbor jadwal produksi, asisten chat AI baca-saja, dan pengingat jadwal. Dilarang membuka data keuangan sensitif & manajemen user. |

_Penambahan peran lebih granular (jika dibutuhkan kelak) ditandai `[Perlu Konfirmasi Tim]`._

---

## 3. Alur Bisnis Utama & Cakupan Fitur

### 3.1 Alur Penggunaan Utama (End-to-End MVP)

1. Pengelola atau staf operasional login dan memasukkan pesanan (pemesan, menu, jumlah porsi, tanggal acara, alamat, catatan).
2. Backend Express mengambil **harga resmi langsung dari database `Menu`** (tidak memercayai harga dari client), menghitung kebutuhan bahan baku otomatis dari resep standar dengan **konversi satuan baku (`gram ↔ kg`, `ml ↔ liter`)**, membuat `Order` (`DRAFT`), dan otomatis menerbitkan **Invoice digital** (`UNPAID`).
3. Pengelola mencatat pembayaran DP (minimal 60% `[Menunggu Konfirmasi PIC]`) → status invoice berubah menjadi `PARTIALLY_PAID` dan pesanan dikonfirmasi (`CONFIRMED`), lalu mencatat pelunasan → `PAID`; **PDF Invoice Pesanan** diunduh/dicetak melalui modul keuangan (`FS-06`).
4. Pesanan, status pembayaran (sesuai RBAC), dan jadwal produksi tampil di dasbor jadwal secara responsif dan mudah dipahami staf senior di desktop maupun ponsel.
5. Sebagai pengayaan: pengguna dapat bertanya melalui chatbot **Agentic RAG dual-source** (ChromaDB + backend read-only tools PostgreSQL tanpa SQL bebas), memantau dasbor analitik (formula KPI terkunci sejak `DS-02` M2, estimasi bahan dari forecasting per menu `DS-05` + resep `FS-04`, sentimen `AI-03`), mengunduh **PDF Laporan Analitik + AI Business Insight (`FS-08` + `AI-06`)**, serta menerima pengingat otomatis anti-duplikasi.

### 3.2 Daftar Fitur Lengkap (Wajib & Tambahan)

#### A. Fitur Wajib (Main Quest — Target MVP)

1. **Input & Manajemen Pesanan (`FS-05`):** pencatatan pemesan, menu, jumlah porsi, tanggal acara, alamat, dan catatan; **validasi harga langsung dari database backend**, validasi Joi menolak input kosong/tidak valid dengan pesan spesifik per kolom.
2. **Katalog Menu, Resep Standar & Kalkulator Bahan Baku (`FS-04`):** perhitungan otomatis presisi kebutuhan bahan baku + konversi satuan baku dari jumlah porsi (identik dengan hitungan manual pada 10, 50, dan 100 nasi box) beserta peringatan bila menu belum memiliki resep.
3. **Invoice Digital, DP 60%, Pelunasan & PDF Invoice (`FS-06`):** penerbitan invoice otomatis (`1:1` per order), **PDF Invoice Pesanan** di backend Express, pencatatan DP (minimal 60% terkonfigurasi `[Menunggu Konfirmasi PIC]`) yang mengonfirmasi pesanan, pelunasan, sisa tagihan, dan status pembayaran (`UNPAID` -> `PARTIALLY_PAID` -> `PAID`).
4. **Dasbor Jadwal & Informasi Pesanan (`FS-01`, `FS-05`):** antarmuka sederhana, responsif di ponsel (`390x844`) & desktop (`1440x900`), ramah staf senior sehingga staf dapat menemukan & menjelaskan detail pesanan mandiri tanpa bertanya ke pengelola.
5. **Fondasi Aplikasi, Autentikasi, RBAC & Akses Publik (`FS-02`, `FS-03`, `OPS-01..03`):** login/logout, pembatasan peran `ADMIN` vs `STAFF` di backend Express, validasi Joi, penyimpanan persisten PostgreSQL via Prisma, status umpan balik jelas (_loading/sukses/gagal_), dan deployment publik desktop/ponsel.
6. **Pengolahan & Analisis Data UMKM (`DS-01`, `DS-02`, `DS-03`, `DS-06`):** wrangling (gathering, assessing, cleaning, anonimasi PII & tanpa data gaji), kamus data, penandaan `is_synthetic`, jawaban 5 pertanyaan bisnis + **penguncian definisi KPI dasbor di M2**, temuan & rekomendasi, serta audit akurasi akhir.
7. **Chatbot Generatif + Model Relevansi 2 Kelas (`AI-01`, `AI-02`, `AI-04`, `AI-05`, `FS-07`):** model klasifikasi **relevansi 2 kelas** (`relevant` vs `out_of_domain`, tanpa klasifikasi intent) latih sendiri dari data DS (perbandingan >= 2 model dengan F1-score di README), RAG menu/SOP lewat ChromaDB tervalidasi PIC, API LLM melalui backend proxy Express, riwayat chat tersimpan di DB, serta penolakan pertanyaan tanpa sumber.
8. **Pengukuran Waktu Proses & Dokumentasi/Pengujian Akhir (`FS-09`, `DS-06`):** pencatatan baseline manual vs waktu sistem pada demonstrasi 100 nasi box (dilaporkan sebagai hasil teramati), Swagger/OpenAPI + Scalar `/docs`, README evaluasi lengkap, user manual, dan uji end-to-end.

#### B. Fitur Tambahan (Side Quest — Nilai Tambah; tidak boleh menunda alur utama)

9. **Arsitektur Decoupled & Kolaborasi Modern (`FS-01`, `FS-03`, `OPS-01`, `OPS-03`):** frontend Next.js + Tailwind CSS + shadcn/ui + Axios BFF terpisah dari Express REST `/api/v1` + FastAPI, App Mockup, dokumentasi keputusan desain responsif, dan deployment free tier.
10. **Chatbot Agentic RAG Dual-Source & Guardrail Keamanan (`AI-04`, `AI-05`, `FS-07`):** LLM tool calling ke **dua sumber utama**—(1) Knowledge base via embedding + ChromaDB (menu, FAQ, SOP, aturan pembayaran dengan 4 metadata: sumber, tanggal, versi, validasi; evaluasi `Hit@3`) dan (2) Database operasional PostgreSQL via **backend read-only tools Express** (pesanan, invoice, status DP, pelunasan, jadwal aktual) **tanpa akses SQL bebas kepada LLM**, prompt template + few-shot **tanpa klasifikasi intent**, RBAC diverifikasi backend, proteksi & log keamanan _prompt injection_, uji >= 10 pertanyaan luar konteks, dan validasi anti-halusinasi.
11. **Forecasting Permintaan per Menu & Estimasi Bahan (`DS-04`, `DS-05`, `FS-08`):** perbandingan **objektif** baseline Moving Average vs Random Forest pada _chronological split_, studi ablasi fitur lag/rolling, tuning, evaluasi MAE/RMSE/WAPE, serta penggabungan prediksi per menu dengan resep standar (`FS-04`) untuk estimasi bahan baku di dasbor.
12. **Analisis Sentimen Feedback Pelanggan (`AI-03`):** klasifikasi sentimen 2 kelas (`positive`/`negative`), pemeriksaan distribusi & imbalance handling, perbandingan baseline vs tuning, uji teks campuran & kosong, analisis error, pelabelan jelas data sintetis bukan feedback nyata, dan integrasi ke dasbor analitik.
13. **AI Business Insight & PDF Laporan Analitik (`AI-06`, `OPS-04`, `FS-08`):** SLM/LLM open-source di-host mandiri di Modal GPU (vLLM, siap M2) untuk menghasilkan narasi insight JSON (`AI-06`, evaluasi 10 laporan + latensi + fallback deterministik tanpa menggantikan RAG), yang dirender menjadi **PDF Laporan Analitik oleh backend Express `FS-08`**.
14. **Dasbor Analitik Interaktif (`FS-08`, `DS-02`, `DS-06`):** indikator KPI (formula terkunci di `DS-02` M2), filter periode & status, unggah data `.csv`/`.xlsx` bervalidasi, tampilan forecasting + estimasi bahan, sentimen, AI Insight, dan unduhan **PDF Laporan Analitik**.
15. **Reminder Otomatis & Kanal WhatsApp WAHA (`FS-09`, `AI-07`, `OPS-05`):** 4 jenis pengingat (pesanan terdekat H-1, pembayaran belum lunas, ringkasan keuangan mingguan khusus `ADMIN`, saran bahan baku) via in-app, WhatsApp WAHA (nomor cadangan izin PIC, whitelist staf terdaftar + penegakan RBAC, fallback Cloud API uji/in-app/email), dan email opsional, dijadwalkan cron + worker Node.js VPS tanpa Redis/BullMQ (kode selesai ≤ Feature Freeze M3; anti-duplikasi & retry diuji di M4).

### 3.3 Pemetaan Fitur ke 27 Technical Issue Specification

| Area               | ID Issue | Ringkasan Fitur & Cakupan                                                                                                                                                                                                        | Quest       | Prioritas       | Milestone |
| ------------------ | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------- | --------------- | --------- |
| **Full-Stack**     | `FS-01`  | App Mockup, desain responsif (`390px` & `1440px`), App Shell staf senior (tombol >= 44px, WCAG AA), & dokumentasi alasan desain                                                                                                  | Main + Side | `P0-blocker`    | `M1`      |
| **Full-Stack**     | `FS-02`  | Skema Prisma PostgreSQL 17 (termasuk konversi satuan bahan, `isSynthetic`, `User.whatsappNumber`, `ChatLog` lengkap, `NotificationLog` idempotency)                                                                              | Main + Side | `P0-blocker`    | `M1`      |
| **Full-Stack**     | `FS-03`  | Autentikasi, RBAC backend-enforced (`ADMIN`/`STAFF`), `X-Internal-Token`, validasi Joi `/api/v1`, error RFC 9457, OpenAPI 3.1.0 + Scalar `/docs`                                                                                 | Main + Side | `P0-blocker`    | `M1`      |
| **Full-Stack**     | `FS-04`  | Katalog menu (single source harga), resep standar, kalkulator bahan presisi & konversi satuan (`gram ↔ kg`, `ml ↔ liter`), peringatan resep kosong                                                                               | Main        | `P1-mvp`        | `M2`      |
| **Full-Stack**     | `FS-05`  | Input pesanan (harga divalidasi dari DB, otomatis terbit invoice `UNPAID`), state machine `OrderStatus`, & dasbor jadwal produksi ramah staf senior                                                                              | Main        | `P1-mvp`        | `M2`      |
| **Full-Stack**     | `FS-06`  | Invoice digital, DP minimal 60% terkonfigurasi `[Menunggu Konfirmasi PIC]` → konfirmasi order, pelunasan, & **PDF Invoice Pesanan**                                                                                              | Main        | `P1-mvp`        | `M3`      |
| **Full-Stack**     | `FS-07`  | Proxy Chat AI (`/api/v1/chat/*`), **Backend Read-Only Tools DB** (`/api/v1/internal/agent-tools/*`, tanpa SQL bebas, RBAC backend), simpan `ChatLog`, & UI Chat                                                                  | Main + Side | `P1-mvp`        | `M3`      |
| **Full-Stack**     | `FS-08`  | Dasbor analitik interaktif (KPI dari `DS-02`), filter, upload `.csv`/`.xlsx`, gabung forecasting per menu `DS-05` + resep `FS-04` → estimasi bahan, sentimen, AI Insight & **PDF Laporan Analitik**                              | Side        | `P2-side-quest` | `M3`      |
| **Full-Stack**     | `FS-09`  | 4 jenis pengingat otomatis & 3 kanal (kode selesai ≤ Feature Freeze M3), User Manual, ukur waktu proses sistem vs baseline manual, & uji E2E 100 nasi box (M4)                                                                   | Main + Side | `P1-mvp`        | `M4`      |
| **Data Science**   | `DS-01`  | Pengumpulan, anonimisasi (0 PII & 0 data gaji), assessing, & cleaning data Spreadsheet UMKM (`data/raw/` lokal di-ignore Git)                                                                                                    | Main        | `P0-blocker`    | `M1`      |
| **Data Science**   | `DS-02`  | EDA 5 pertanyaan bisnis, perbandingan dengan Spreadsheet asli izin PIC, rekomendasi operasional, & **penguncian definisi formula KPI dasbor** sebelum `FS-08` M3                                                                 | Main + Side | `P1-mvp`        | `M2`      |
| **Data Science**   | `DS-03`  | Kamus data & satuan baku (`data/dictionary/`), generator data sintetis (`is_synthetic = true`) + dokumentasi README, & paket train/test bebas _leakage_ untuk AI/DS                                                              | Main + Side | `P0-blocker`    | `M1`      |
| **Data Science**   | `DS-04`  | Rekayasa fitur lag/rolling & evaluasi **objektif** forecasting permintaan **per menu** (Moving Average vs Random Forest + ablasi fitur + tuning; MAE, RMSE, WAPE)                                                                | Side        | `P2-side-quest` | `M2`      |
| **Data Science**   | `DS-05`  | Serving pipeline inferensi forecasting **per menu** ke FastAPI (`POST /api/v1/ml/forecast/demand`), penanganan data kosong/sedikit, & status `isSyntheticTrained`                                                                | Side        | `P2-side-quest` | `M3`      |
| **Data Science**   | `DS-06`  | Verifikasi implementasi KPI dasbor (`FS-08` vs definisi `DS-02`), audit estimasi bahan & angka `AI-06`, serta audit akhir `is_synthetic` & 0 PII/gaji                                                                            | Main + Side | `P1-mvp`        | `M4`      |
| **AI Engineering** | `AI-01`  | Dokumentasi masalah AI di README, kontrak OpenAPI 3.1.0 + Scalar `/docs`, & kerangka serving FastAPI `:8001` _(CLOSED / Selesai)_                                                                                                | Main + Side | `P0-blocker`    | `M1`      |
| **AI Engineering** | `AI-02`  | Model AI latih sendiri: **klasifikasi relevansi dua kelas** (`relevant` vs `out_of_domain`, tanpa klasifikasi intent), banding >= 2 model F1-score di README, imbalance & tuning                                                 | Main        | `P1-mvp`        | `M2`      |
| **AI Engineering** | `AI-03`  | Model tambahan: klasifikasi sentimen 2 kelas (`positive`/`negative`), distribusi, imbalance, tuning, uji teks campuran/kosong, error analysis, & label `is_synthetic`                                                            | Side        | `P2-side-quest` | `M2`      |
| **AI Engineering** | `AI-04`  | Kurasi knowledge base tervalidasi PIC (`data/knowledge/`, 4 metadata: sumber/tanggal/versi/validasi) & ChromaDB VectorStore Adapter (uji M1, evaluasi `Hit@3`)                                                                   | Main + Side | `P1-mvp`        | `M1`      |
| **AI Engineering** | `AI-05`  | **Agentic RAG Dual-Source** (ChromaDB + backend read-only tools DB `FS-07`, tanpa SQL bebas & tanpa klasifikasi intent), prompt+few-shot, RBAC backend, log _prompt injection_, AC `Hit@3`, 10 uji luar konteks, anti-halusinasi | Main + Side | `P1-mvp`        | `M2`      |
| **AI Engineering** | `AI-06`  | Modul AI Business Insight (SLM/LLM open-source via Modal GPU `OPS-04`, evaluasi 10 laporan + latensi, fallback deterministik, narasi JSON untuk PDF Laporan `FS-08`)                                                             | Side        | `P2-side-quest` | `M3`      |
| **AI Engineering** | `AI-07`  | Integrasi kanal WhatsApp WAHA (nomor cadangan izin PIC, whitelist + RBAC user DB, simpan `ChatLog`, kirim reminder `FS-09`) & uji resiliensi putus WAHA/AI mati                                                                  | Side        | `P2-side-quest` | `M3`      |
| **DevOps / Infra** | `OPS-01` | Tata kelola Git/PR (default branch `dev`, PR template `Closes #N`), GitHub Actions CI (`workflow_dispatch`), secrets hygiene, uji kelayakan layanan M1, & tinjauan visibilitas repo                                              | Main + Side | `P0-blocker`    | `M1`      |
| **DevOps / Infra** | `OPS-02` | Docker Compose produksi VPS (`api`, `ai-service`, `worker`, `postgres`, `chroma`, opt-in `waha`, tanpa Redis/BullMQ) + reverse proxy HTTPS/TLS & isolasi port                                                                    | Main + Side | `P1-mvp`        | `M2`      |
| **DevOps / Infra** | `OPS-03` | Deployment frontend Next.js di Vercel (free tier), env server-only `API_BASE_URL`, CORS aman, uji desktop/ponsel + restart layanan + putus DB, & dokumentasi README                                                              | Main + Side | `P1-mvp`        | `M2`      |
| **DevOps / Infra** | `OPS-04` | Deployment SLM/LLM open-source di Modal GPU (vLLM, Bearer auth, auto-suspend idle timeout, pantau cold-start & kredit, siap sebelum `AI-06` M3)                                                                                  | Side        | `P2-side-quest` | `M2`      |
| **DevOps / Infra** | `OPS-05` | Penjadwalan cron sistem VPS untuk worker (selesai ≤ Feature Freeze M3), backup/restore Postgres & Chroma, & uji cron ganda anti-duplikasi + failover pra-demo (M4)                                                               | Side        | `P2-side-quest` | `M4`      |

### 3.4 Yang Tidak Dikerjakan (Out-of-Scope MVP)

Sesuai Project Plan A26-CS105, item berikut **eksplisit di luar cakupan MVP**:

- Integrasi payment gateway dan verifikasi pembayaran otomatis.
- Integrasi Shopee atau marketplace eksternal lainnya.
- Aplikasi mobile native Android atau iOS.
- Sistem inventaris dan pengelolaan stok bahan baku secara real-time (`inventory` telah dihapus dari monorepo).
- Perhitungan pembelian bersih berdasarkan stok aktual.
- Forecasting tingkat lanjut untuk operasional komersial dengan jaminan akurasi absolut.
- Chatbot AI untuk percakapan umum di luar informasi dan operasional Catering Si Kembar.
- Pengambilan keputusan bisnis otomatis oleh AI tanpa validasi pengguna.
- Portal pelanggan mandiri untuk pemesanan dan pembayaran online publik.
- Penggunaan aplikasi sebagai sistem produksi komersial penuh, integrasi Telegram, serta instalasi Redis/BullMQ pada fase MVP.

---

## 4. Arsitektur Sistem & Standar Teknis

### 4.1 Topologi & Enam Workspace Monorepo

| Workspace / Direktori                            | Stack Utama                                                                                                                                                                        | Target Runtime & Boundary                                                                                                                                                                      |
| ------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `@smart-catering/web` (`apps/web`)               | Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS, shadcn/ui, Axios                                                                                                      | **Vercel (free tier)**. Memakai BFF Route Handlers `/api/*` menuju `API_BASE_URL` server-only. Dilarang impor DB/secret server atau memanggil `apps/ai-service` langsung.                      |
| `@smart-catering/api` (`apps/api`)               | Express 5.3.0, TypeScript (`apps/api/src/` -> `dist/src/index.js`), Joi 18.3.2, `cors`, `helmet`, Prisma                                                                           | **VPS (`127.0.0.1:3001` di balik TLS proxy)**. Pemilik rute `/api/v1/*`, modul bisnis (`auth`, `menus`, `orders`, `finance`, `analytics`, `chat`, `reminders`), & integrasi (`waha`, `email`). |
| `@smart-catering/ai-service` (`apps/ai-service`) | Python 3.12 (`uv`), FastAPI, Pydantic, Uvicorn, `scalar-fastapi`; optional extras `rag` (`chromadb`, `langchain`, `langgraph`, `httpx`), `ml` (`scikit-learn`, `pandas`, `joblib`) | **VPS jaringan internal `:8001` saja** (tanpa eksposur publik). Pemilik `app/{rag,chroma,insight,ml/{relevance,forecasting,sentiment}}`.                                                       |
| `@smart-catering/worker` (`apps/worker`)         | Node.js 24, TypeScript (`apps/worker/src/` -> `dist/index.js`)                                                                                                                     | **VPS jaringan internal `:3002` saja**. Dipicu cron sistem VPS. Independen: dilarang mengimpor internal `apps/api` atau `apps/ai-service`.                                                     |
| `@smart-catering/db` (`packages/db`)             | Prisma 7 + `@prisma/adapter-pg` + PostgreSQL 17                                                                                                                                    | Shared package server-only (`browser: null`).                                                                                                                                                  |
| `@smart-catering/types` (`packages/types`)       | TypeScript ESM                                                                                                                                                                     | Shared wire contracts lintas workspace tanpa provider/secret.                                                                                                                                  |
| Ruang kerja tim tambahan                         | `data/{raw,synthetic,knowledge,dictionary}`, `notebooks/`, `infra/{docker,modal}`, `docs/spec/`                                                                                    | `data/raw/*` & `.ipynb_checkpoints/` diabaikan `.gitignore` agar data mentah tidak pernah masuk Git.                                                                                           |

### 4.2 Tech Stack Lengkap

| Lapisan / Komponen                                    | Teknologi & Versi Utama                                                                                                                                                                                                | Peran dalam Sistem                                                                                                                   |
| ----------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| **Monorepo & Runtime Node**                           | Node.js `24.15.0`, npm `12.1.0` (Workspaces), Turborepo `2.11.10`, TypeScript `5.9.3`                                                                                                                                  | Pengelolaan 6 workspace dengan 1 `package-lock.json` root dan build/lint/test terorkestrasi                                          |
| **Frontend (`apps/web`)**                             | Next.js `16.4.5` (App Router), React `19.3.1`, Tailwind CSS v4, shadcn/ui (`lucide-react`, `clsx`, `tailwind-merge`, `cva`), Axios                                                                                     | Antarmuka responsif ramah staf senior & pola BFF (`/api/*` -> `API_BASE_URL` server-only)                                            |
| **Backend API (`apps/api`)**                          | Express `5.3.0`, TypeScript (`apps/api/src/`), Joi `18.3.2`, `cors`, `helmet`, OpenAPI `3.1.0`, Scalar (`@scalar/api-reference@1.76.4`), generator PDF server-side                                                     | REST API transaksional `/api/v1/*`, autentikasi/RBAC, validasi skema, kalkulator bahan, invoice PDF, dan proxy ke AI service         |
| **Database & Vector Store**                           | PostgreSQL `17`, Prisma `7.10.1` (`@prisma/adapter-pg`), ChromaDB (`1.5.9`)                                                                                                                                            | Penyimpanan persisten transaksi/riwayat chat (PostgreSQL) dan indeks dokumen pengetahuan RAG (ChromaDB)                              |
| **AI Service & DS (`apps/ai-service`, `notebooks/`)** | Python `3.12` (`>=3.12,<3.14`), `uv` `0.13.7`, FastAPI `0.162.0`, Pydantic `2.14.2`, Uvicorn `0.54.0`, `scalar-fastapi` `1.9.1`, `scikit-learn` `1.9.1`, `langchain` `1.4.8`, `langgraph`, `pandas`, `joblib`, `httpx` | Serving model relevansi 2 kelas, sentimen, forecasting (MA vs Random Forest), retrieval ChromaDB, Agentic RAG, dan client AI Insight |
| **Generative AI & SLM GPU**                           | Proprietary LLM API (Gemini/OpenAI `[Perlu Konfirmasi Tim]`), Model Embedding (lokal/API `[Perlu Konfirmasi Tim]`), Modal GPU + vLLM (SLM/LLM open-source)                                                             | Generasi jawaban Agentic RAG (API LLM) dan ringkasan AI Business Insight (SLM/LLM open-source di Modal GPU)                          |
| **Worker & Kanal Notifikasi**                         | Node.js Worker (`apps/worker`) + Cron sistem VPS, WAHA Docker opt-in (fallback WhatsApp Cloud API nomor uji), SMTP / SendGrid opsional                                                                                 | Pengingat jadwal & pembayaran otomatis anti-duplikasi tanpa Redis/BullMQ                                                             |
| **Quality, Testing & CI/CD**                          | ESLint `9`, Prettier `3.9`, Vitest `5.1` (V8 coverage >= 80%), Ruff `0.17`, Mypy `2.4`, Pytest `9.2` (`pytest-cov` >= 80%), GitHub Actions CI (`dev`)                                                                  | Penjaga mutu kode lintas TypeScript & Python, validasi kontrak REST, dan build image Docker VPS                                      |
| **Deployment & Infrastruktur**                        | Vercel (free tier — `apps/web`), VPS Ubuntu + Docker Compose + Reverse Proxy TLS (`api`, `ai-service`, `worker`, `postgres`, `chroma`, `waha`), Modal Serverless GPU (`infra/modal/`)                                  | Topologi deployment hybrid yang memisahkan frontend serverless dari layanan backend/AI/data always-on                                |

### 4.3 Standar Kontrak Wire REST, Error & OpenAPI Scalar

Berlaku seragam pada **`apps/api`** dan **`apps/ai-service`** (rincian lengkap di [architecture.md](architecture.md) & [issues/README.md](spec/issues/README.md)):

- **Envelope sukses (`200` / `201`):** `{ "data": ..., "meta": { "requestId": "<uuid>" } }` (+ `meta.pagination: { page, limit, total, totalPages }` untuk endpoint list). Mutasi tanpa body memakai `204 No Content`.
- **Standar error (RFC 9457):** semua error (`400`, `401`, `403`, `404`, `405`, `409`, `422`, `500`, `503`, `504`) mengembalikan `Content-Type: application/problem+json` dengan `type`, `title`, `status`, `detail`, `instance`, `requestId` (+ `errors: [{ path, code, message }]` untuk `422`). Error `500` teredaksi tanpa membocorkan stack trace, SQL, atau env.
- **Korelasi request:** header `X-Request-Id` (UUID kanonis v1–v8 dinormalisasi lowercase, atau UUIDv4 baru bila kosong/tidak valid).
- **Dokumentasi OpenAPI 3.1.0 & Scalar (`/docs`):** tersedia di `/api/openapi` (Express) dan `/openapi.json` (FastAPI) dengan Scalar UI (`@scalar/api-reference@1.76.4`) di `/docs`. Produksi bersifat **fail-closed**: default `404` saat `DOCS_ENABLED` tidak aktif; jika `DOCS_ENABLED=true`, wajib TLS + HTTP Basic Auth dengan `DOCS_PASSWORD` >= 32 karakter.
- **Pengecualian Worker ([ADR-0004](decisions/0004-independent-worker.md)):** `apps/worker` bukan backend REST bisnis; liveness `:3002/health` mengembalikan `{"status":"ok","service":"worker"}` mentah tanpa envelope maupun Scalar `/docs`.
- **Enum status standar lintas modul:**
  - `OrderStatus`: `DRAFT`, `CONFIRMED`, `IN_PREPARATION`, `READY`, `DELIVERED`, `CANCELLED`.
  - `PaymentStatus`: `UNPAID`, `PARTIALLY_PAID`, `PAID`.

### 4.4 Isolasi Dua Sumber Environment

- **Root `.env`** (dari `.env.example`): sumber tunggal backend (`api`, `ai-service`, `worker`), Prisma CLI, dan Docker Compose, disaring per layanan lewat allowlist (`scripts/service-environment.mjs` & `apps/ai-service/app/config.py`) dengan redaksi rahasia di log/`__repr__`.
- **Frontend `apps/web/.env`** (dari `apps/web/.env.example`): hanya `NEXT_PUBLIC_APP_NAME` dan `API_BASE_URL` (server-only). Tidak ada file `.env` tambahan di workspace backend.

---

## 5. Persyaratan Non-Fungsional & Guardrail Wajib

### 5.1 Keamanan, Privasi & Reliabilitas

- **Rahasia & PII:** nol API key, password, token, atau data pribadi nyata pelanggan/UMKM di kode sumber, contoh payload, repositori Git, maupun video demo. Data operasional primer wajib dianonimkan.
- **Otorisasi di server:** pemeriksaan hak akses (`ADMIN` vs `STAFF`) dan proteksi data keuangan ditegakkan di backend Express, bukan sekadar instruksi prompt LLM.
- **Ketahanan terhadap kegagalan AI/DS (_graceful degradation_):** jika FastAPI, API LLM, ChromaDB, atau Modal GPU lambat, kehabisan kuota, atau mati, alur inti operasional (pesanan, resep, invoice, jadwal) tetap berjalan normal dengan pesan fallback jelas.
- **Anti-duplikasi pengingat:** eksekusi cron worker ganda pada jadwal yang sama tidak boleh mengirim notifikasi duplikat (`idempotent` berbasis `NotificationLog`).
- **UX Ramah Staf Senior:** navigasi maksimal 2 ketukan, label bahasa Indonesia lugas, kontras >= WCAG AA (4.5:1), area sentuh >= 44x44 px, dan 0 overflow horizontal di ponsel `390x844` maupun desktop `1440x900`.
- **Kualitas & Coverage:** TypeScript strict, Mypy strict, Prettier, ESLint, Ruff, serta coverage minimum **80%** pada suite Vitest dan Pytest.

### 5.2 Tindakan yang Dilarang (Rubrik Capstone 3 Learning Path)

| Jalur            | Larangan Mutlak                                                                                                                                                                                                                                                                            |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Full-Stack**   | Menampilkan fitur utama mati / halaman "segera hadir"; membocorkan password/API key; memakai data pribadi nyata tanpa izin/anonimasi.                                                                                                                                                      |
| **Gen AI**       | Memakai model pra-latih TensorFlow Hub sebagai model utama Main Quest; mengganti model latih sendiri dengan panggilan langsung ChatGPT/Gemini API; memakai AutoML; melakukan _forking_ proyek AI orang lain.                                                                               |
| **Data Science** | Memakai data tanpa dokumentasi sumber/pembuatan; menyamarkan data dummy/sintetis sebagai data operasional nyata (wajib flag `is_synthetic`); memanipulasi data untuk memoles hasil; membuat klaim dampak bisnis tanpa bukti analisis; mempublikasikan PII/data bisnis sensitif tanpa izin. |

---

## 6. Jadwal Milestone 1 Bulan (`M1`–`M4`)

| Milestone                                    | Rentang Waktu     | Target Utama                                                                                                                                                                                                                                     | Issue Terkait                                                                               |
| -------------------------------------------- | ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------- |
| **M1 — Rancangan Disepakati**                | 21–27 Nov 2026    | Konfirmasi PIC, baseline waktu manual, mockup, skema DB, kontrak API, dataset awal + kamus data, konfigurasi ChromaDB (target 23 Nov), CI & uji kelayakan layanan                                                                                | `FS-01`, `FS-02`, `FS-03`, `DS-01`, `DS-03`, `AI-01`, `AI-04`, `OPS-01`                     |
| **M2 — Fitur Inti Tersedia**                 | 28 Nov–4 Des 2026 | Katalog menu/resep & konversi satuan, input pesanan (harga DB) + invoice awal, EDA & **kunci definisi KPI**, model relevansi 2 kelas, forecasting per menu (MA vs RF), sentimen, RAG dasar, VPS, Vercel, & **Modal GPU**                         | `FS-04`, `FS-05`, `DS-02`, `DS-04`, `AI-02`, `AI-03`, `AI-05`, `OPS-02`, `OPS-03`, `OPS-04` |
| **M3 — Alur Utama Selesai & Feature Freeze** | 5–11 Des 2026     | DP/pelunasan + PDF Invoice (`FS-06`), Chat AI + read-only tools DB (`FS-07`), Dasbor Analitik + estimasi bahan + PDF Laporan (`FS-08`), serving forecasting per menu, AI Insight, WAHA, kode reminder & cron VPS; **Feature Freeze 11 Des 2026** | `FS-06`, `FS-07`, `FS-08`, `DS-05`, `AI-06`, `AI-07` _(kode `FS-09`/`OPS-05` ≤ 11 Des)_     |
| **M4 — Validasi & Finalisasi**               | 12–20 Des 2026    | Pasca feature freeze: pengujian 20 skenario, uji cron ganda anti-duplikasi & failover, verifikasi KPI & audit data akhir, demo **100 nasi box** bersama PIC, ukur waktu sistem vs baseline, bugfix, README & user manual                         | `FS-09`, `DS-06`, `OPS-05`                                                                  |

---

## 7. Daftar Risiko & Item Menunggu Konfirmasi

### 7.1 Item Terbuka (Tanpa Asumsi Terselubung)

- **`[Menunggu Konfirmasi PIC]`:**
  1. Aturan DP minimal 60% (apakah _hard block_ atau boleh disetujui khusus pelanggan tetap).
  2. Formula baku resep, takaran gramatur, dan harga resmi menu paket nasi box UMKM.
  3. Ekspor rekap Spreadsheet pesanan historis teranonimasi sebagai data primer.
  4. Persetujuan tertulis ruang lingkup fitur tambahan dan penyediaan nomor WhatsApp cadangan khusus uji WAHA.
  5. Pencatatan baseline waktu hitung bahan dan penerbitan invoice manual bersama mitra.
- **`[Perlu Konfirmasi Tim]`:**
  1. Penyelarasan visibilitas repositori (Project Plan mewajibkan `private`; saat ini sementara `public` selama fase awal).
  2. Transport autentikasi web BFF (`HttpOnly cookie` vs `Authorization: Bearer`), skema final `/api/v1/internal/agent-tools/*`, dan batas timeout LLM/Modal GPU.
  3. Provider proprietary LLM API (Gemini vs OpenAI), model embedding (lokal multilingual vs API), bobot SLM Modal GPU (`Qwen2.5-7B-Instruct` vs `Llama-3.2-3B`/kuantisasi), serta kredensial SMTP email opsional.
  4. Definisi matematis final KPI (omzet `Order CONFIRMED` vs `Payment` masuk), domain/subdomain VPS untuk TLS, dan batas _chronological holdout split_ forecasting.

### 7.2 Mitigasi Risiko Kritis

- **Keterlambatan fitur tambahan:** kontrak API & alur inti dikunci di M1–M2 dan **Feature Freeze pada 11 Des 2026**; fitur tambahan tidak boleh menunda alur utama.
- **Gangguan API LLM / Modal GPU:** timeout, retry terbatas, fallback pesan ramah untuk RAG, dan fallback ringkasan deterministik untuk AI Business Insight (tanpa mencampur SLM insight ke jalur RAG).
- **Risiko blokir nomor WAHA:** wajib memakai nomor cadangan berizin PIC, whitelist khusus nomor staf terdaftar dengan volume rendah, serta opsi cadangan WhatsApp Cloud API nomor uji atau pengingat in-app/email.
- **Prompt injection & kebocoran data:** hak akses ditegakkan di backend Express, chatbot hanya memakai tool baca-saja, percobaan injection dicatat di log, dan minimal 10 pertanyaan luar konteks diuji serta didokumentasikan.

---

## 8. Rencana Pengujian & Alur Kolaborasi GitHub

### 8.1 Cakupan 20 Skenario Pengujian

Pengujian internal berjalan paralel sejak M2 hingga uji final M4 mencakup seluruh 20 skenario di [Project Plan §6](Asah_2026_Project_Plan_A26-CS105.md#6-rencana-pengujian): input pesanan (termasuk 100 nasi box & input tidak valid), perhitungan bahan baku (10/50/100 porsi & menu tanpa resep), invoice & DP 60%/pelunasan, dasbor jadwal di ponsel untuk staf senior, autentikasi & RBAC, kesesuaian kontrak API/OpenAPI, Agentic RAG + 10 pertanyaan luar konteks, kualitas retrieval (`Hit@3` + metadata PIC), keamanan prompt injection, kegagalan layanan AI, forecasting (MA vs RF, fitur lag/rolling, tuning), analisis sentimen, AI Business Insight (10 laporan + PDF + latensi), dasbor analitik (filter & upload valid/salah), reminder otomatis anti-duplikasi cron, WAHA whitelist & sesi putus, pengukuran waktu proses sistem vs baseline, perbandingan 2 model relevansi, deployment responsif + restart layanan/putus DB, serta alur end-to-end 100 nasi box bersama PIC.

Hasil pengujian dicatat pada tiga tempat: **Spreadsheet pengujian bersama**, **GitHub Issues** (bug & perbaikan), dan **README** (kualitas dataset, distribusi kelas, tuning, metrik evaluasi, perbandingan model, arsitektur RAG, dan 10 uji luar konteks).

### 8.2 Alur Kerja Repository & CI

- **Branch kerja:** seluruh PR ditargetkan ke branch **`dev`** (direkomendasikan sebagai default branch GitHub dengan branch protection).
- **Template PR:** [.github/pull_request_template.md](../.github/pull_request_template.md) otomatis termuat saat PR dibuka; gunakan `Closes #<nomor-issue>` agar issue tertutup otomatis saat merge dan kartu berpindah ke `Done` di [GitHub Project #1](https://github.com/orgs/Catering-Si-Kembar/projects/1).
- **CI Otomatis:** [.github/workflows/ci.yml](../.github/workflows/ci.yml) menjalankan job `unit-tests` (coverage Node + Python) dan `quality` (`format:check`, `lint`, `db:validate`, `db:generate`, `typecheck`, `build`, `smoke`, validasi Compose, dan build image VPS) pada setiap push dan PR ke `dev`.

---

## 9. Dokumen Turunan

- [Project Plan A26-CS105](Asah_2026_Project_Plan_A26-CS105.md) — sumber bisnis, jadwal, risiko, & 20 skenario uji.
- [Indeks 27 Technical Issue Specification](spec/issues/README.md) — spesifikasi siap implementasi per area (`01-fullstack.md`, `02-data-science.md`, `03-ai-engineering.md`, `04-devops-infra.md`).
- [Arsitektur](architecture.md) · [Struktur Repository](repository-structure.md) · [ADR](decisions/README.md) ([ADR-0005 Express + Joi](decisions/0005-express-joi-api-v1.md)).
- [Development](development.md) · [Environment](environment.md) · [Deployment Vercel](deployment-vercel.md) · [Deployment VPS](deployment-vps.md) · [PRD Fase 0 (Historis)](PRD_FASE_0.md).
