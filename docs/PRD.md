# Product Requirements Document (PRD) — Smart Catering

**Versi:** 3.0 · **Diperbarui:** 2026-11-24 · **ID Tim:** A26-CS105 · **Mitra UMKM:** Catering Si Kembar  
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
2. Sistem menghitung kebutuhan bahan baku otomatis berdasarkan resep standar per porsi dan menghitung total harga pesanan.
3. Sistem menerbitkan invoice digital yang dapat dilihat, dicetak, atau diunduh dalam format PDF.
4. Pengelola mencatat pembayaran DP (minimal 60% `[Menunggu Konfirmasi PIC]`) serta pelunasan sisa tagihan, memperbarui status `PaymentStatus` (`UNPAID` -> `PARTIALLY_PAID` -> `PAID`).
5. Pesanan, status pembayaran, dan jadwal produksi tampil di dasbor jadwal sesuai hak akses (`ADMIN` / `STAFF`) dan mudah dibaca di ponsel.
6. Sebagai fitur tambahan: pengguna dapat bertanya ke chatbot Agentic RAG, memantau dasbor analitik & forecasting, mengunduh ringkasan AI Business Insight PDF, serta menerima pengingat otomatis.

### 3.2 Daftar Fitur Lengkap (Wajib & Tambahan)

#### A. Fitur Wajib (Main Quest — Target MVP)

1. **Input & Manajemen Pesanan (`FS-05`):** pencatatan pemesan, menu, jumlah porsi, tanggal acara, alamat, dan catatan; validasi menolak input kosong/tidak valid dengan pesan spesifik per kolom.
2. **Katalog Menu, Resep Standar & Kalkulator Bahan Baku (`FS-04`):** perhitungan otomatis total kebutuhan bahan baku dari jumlah porsi (teruji pada 10, 50, dan 100 nasi box) beserta peringatan bila menu belum memiliki resep.
3. **Invoice Digital, DP 60% & Pelunasan (`FS-06`):** penerbitan invoice otomatis yang dapat dicetak/diunduh (PDF), pencatatan DP (minimal 60% `[Menunggu Konfirmasi PIC]`), pelunasan, sisa tagihan, dan status pembayaran (`UNPAID` -> `PARTIALLY_PAID` -> `PAID`).
4. **Dasbor Jadwal & Informasi Pesanan (`FS-01`, `FS-05`):** antarmuka sederhana, responsif di ponsel (`390x844`) & desktop (`1440x900`), ramah staf senior sehingga staf dapat menemukan detail pesanan mandiri tanpa bertanya ke pengelola.
5. **Fondasi Aplikasi, Autentikasi, RBAC & Akses Publik (`FS-02`, `FS-03`, `OPS-01..03`):** login/logout, pembatasan peran `ADMIN` vs `STAFF`, validasi Joi, penyimpanan persisten PostgreSQL via Prisma, status umpan balik jelas (_loading/sukses/gagal_), dan deployment publik desktop/ponsel.
6. **Pengolahan & Analisis Data UMKM (`DS-01`, `DS-02`, `DS-03`, `DS-06`):** wrangling (gathering, assessing, cleaning, anonimasi PII), kamus data, penandaan `is_synthetic`, jawaban 5 pertanyaan bisnis (menu favorit, rata-rata porsi, waktu ramai, pola pembayaran, bahan baku utama), temuan & rekomendasi.
7. **Chatbot Generatif + Model Relevansi 2 Kelas (`AI-01`, `AI-02`, `FS-07`):** model klasifikasi relevansi 2 kelas latih sendiri dari data DS (perbandingan >= 2 model dengan metrik F1-score sama di README), API LLM melalui backend proxy, riwayat chat tersimpan di DB, serta penolakan pertanyaan tanpa sumber.
8. **Pengukuran Waktu Proses & Dokumentasi/Pengujian Akhir (`FS-09`, `DS-06`):** pencatatan baseline manual vs waktu sistem pada demonstrasi 100 nasi box (dilaporkan sebagai hasil teramati), Swagger/OpenAPI + Scalar `/docs`, README evaluasi lengkap, user manual, dan uji end-to-end.

#### B. Fitur Tambahan (Side Quest — Nilai Tambah)

9. **Arsitektur Decoupled & Kolaborasi Modern (`FS-01`, `FS-03`, `OPS-01`, `OPS-03`):** frontend Next.js + Tailwind CSS + shadcn/ui + Axios BFF terpisah dari Express REST `/api/v1` + FastAPI, App Mockup, dokumentasi keputusan desain responsif, dan deployment free tier.
10. **Chatbot Agentic RAG & Guardrail Keamanan (`AI-04`, `AI-05`):** model embedding + ChromaDB berisi dokumen tervalidasi PIC (metadata sumber, tanggal, versi, validasi), evaluasi `Hit@3`, API LLM dengan tool calling baca-saja (dokumen & data sistem), prompt template + few-shot, proteksi _prompt injection_, dan uji >= 10 pertanyaan luar konteks _(ekstensi >= 4 kelas intent bersifat opsional)_.
11. **Forecasting Permintaan Menu & Estimasi Bahan (`DS-04`, `DS-05`):** perbandingan baseline Moving Average vs Random Forest dengan _chronological split_, fitur lag & rolling, tuning, evaluasi MAE/RMSE/WAPE, serta integrasi ke dasbor web.
12. **Analisis Sentimen Feedback Pelanggan (`AI-03`):** klasifikasi sentimen >= 2 kelas (positif/negatif), pemeriksaan distribusi & penanganan ketidakseimbangan kelas, tuning, error analysis, dan integrasi ringkasan ke dasbor analitik.
13. **AI Business Insight & Unduhan PDF (`AI-06`, `OPS-04`, `FS-08`):** SLM/LLM open-source di-host mandiri di Modal GPU (vLLM) untuk ringkasan laporan bisnis + rekomendasi, evaluasi 10 sampel laporan, pencatatan latensi, fallback deterministik, dan ekspor PDF.
14. **Dasbor Analitik Interaktif (`FS-08`, `DS-06`):** indikator KPI, filter periode & status, pembaruan data via unggah file `.csv`/`.xlsx` atau database, serta tampilan terpadu forecasting, sentimen, dan AI Insight PDF.
15. **Reminder Otomatis & Kanal WhatsApp WAHA (`FS-09`, `AI-07`, `OPS-05`):** pengingat pesanan terdekat, pelunasan, ringkasan keuangan mingguan (khusus `ADMIN`), dan saran bahan baku melalui kanal in-app, WhatsApp WAHA (khusus nomor staf terdaftar dengan nomor cadangan berizin PIC; fallback WhatsApp Cloud API uji), dan email opsional, dijadwalkan cron + worker Node.js VPS secara idempoten (anti-duplikasi & retry).

### 3.3 Pemetaan Fitur ke 27 Technical Issue Specification

| Area               | ID Issue | Ringkasan Fitur & Cakupan                                                                                                                                                                                                                                                            | Quest       | Prioritas       | Milestone |
| ------------------ | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------- | --------------- | --------- |
| **Full-Stack**     | `FS-01`  | App Mockup, desain responsif mobile (`390px`) & desktop (`1440px`), App Shell ramah staf senior (tombol >= 44px, kontras WCAG AA)                                                                                                                                                    | Main + Side | `P0-blocker`    | `M1`      |
| **Full-Stack**     | `FS-02`  | Skema database Prisma PostgreSQL 17 (`User`, `Customer`, `Menu`, `Ingredient`, `RecipeItem`, `Order`, `OrderItem`, `Invoice`, `Payment`, `ChatLog`, `NotificationLog`), migrasi, & seed aman                                                                                         | Main + Side | `P0-blocker`    | `M1`      |
| **Full-Stack**     | `FS-03`  | Autentikasi, RBAC (`ADMIN`/`STAFF`), validasi Joi `/api/v1`, error RFC 9457, OpenAPI 3.1.0 + Scalar `/docs`                                                                                                                                                                          | Main + Side | `P0-blocker`    | `M1`      |
| **Full-Stack**     | `FS-04`  | Katalog menu, resep standar per porsi, & kalkulator kebutuhan bahan baku otomatis (teruji 10, 50, 100 porsi)                                                                                                                                                                         | Main        | `P1-mvp`        | `M2`      |
| **Full-Stack**     | `FS-05`  | Input & manajemen pesanan (`OrderStatus`), serta dasbor jadwal produksi harian/mingguan ramah staf senior                                                                                                                                                                            | Main        | `P1-mvp`        | `M2`      |
| **Full-Stack**     | `FS-06`  | Invoice digital otomatis, pencatatan DP (min. 60% `[Menunggu Konfirmasi PIC]`), pelunasan, & export PDF                                                                                                                                                                              | Main        | `P1-mvp`        | `M3`      |
| **Full-Stack**     | `FS-07`  | Proxy backend Chat AI (`/api/v1/chat/*` -> FastAPI `/api/v1/rag/chat`), simpan riwayat inferensi DB, & UI Chat + fallback                                                                                                                                                            | Side        | `P2-side-quest` | `M3`      |
| **Full-Stack**     | `FS-08`  | Dasbor analitik interaktif (KPI, filter periode/status, unggah data `.csv`/`.xlsx`, tampilan forecasting, sentimen, AI Insight & PDF)                                                                                                                                                | Side        | `P2-side-quest` | `M3`      |
| **Full-Stack**     | `FS-09`  | Pengingat in-app & email worker idempoten, panduan pengguna (_user manual_), pengukuran waktu proses, & uji E2E 100 nasi box                                                                                                                                                         | Main + Side | `P1-mvp`        | `M4`      |
| **Data Science**   | `DS-01`  | Pengumpulan, anonimasi PII, assessing, & cleaning data Spreadsheet UMKM (`data/raw/` lokal di-ignore Git)                                                                                                                                                                            | Main        | `P0-blocker`    | `M1`      |
| **Data Science**   | `DS-02`  | EDA menjawab 5 pertanyaan bisnis (menu favorit, rata-rata porsi, waktu ramai, pola pembayaran, bahan baku utama) + rekomendasi                                                                                                                                                       | Main        | `P1-mvp`        | `M2`      |
| **Data Science**   | `DS-03`  | Kamus data (`data/dictionary/`), generator data sintetis (`is_synthetic = true`), & paket train/test split bebas _leakage_ untuk Gen AI                                                                                                                                              | Main + Side | `P0-blocker`    | `M1`      |
| **Data Science**   | `DS-04`  | Rekayasa fitur lag/rolling & perbandingan model forecasting (Moving Average vs Random Forest + tuning; MAE, RMSE, WAPE)                                                                                                                                                              | Side        | `P2-side-quest` | `M2`      |
| **Data Science**   | `DS-05`  | Serving pipeline inferensi forecasting ke FastAPI (`POST /api/v1/ml/forecast/demand`) + artefak `apps/ai-service/app/ml/forecasting/artifacts/`                                                                                                                                      | Side        | `P2-side-quest` | `M3`      |
| **Data Science**   | `DS-06`  | Spesifikasi formula KPI dasbor bisnis & audit akurasi data akhir sebelum demonstrasi                                                                                                                                                                                                 | Main + Side | `P1-mvp`        | `M4`      |
| **AI Engineering** | `AI-01`  | Dokumentasi masalah AI di README, kontrak OpenAPI 3.1.0 + Scalar `/docs`, & kerangka serving FastAPI `:8001`                                                                                                                                                                         | Main + Side | `P0-blocker`    | `M1`      |
| **AI Engineering** | `AI-02`  | Model AI latih sendiri: **klasifikasi 2 kelas relevansi** (`relevant` vs `out_of_domain`) pada `POST /api/v1/ml/predict-relevance` (banding >= 2 model, imbalance, tuning, F1-score); ekstensi >= 4 kelas intent (`POST /api/v1/ml/predict-intent`) bersifat **opsional** Side Quest | Main + Side | `P1-mvp`        | `M2`      |
| **AI Engineering** | `AI-03`  | Model tambahan: analisis sentimen feedback pelanggan (>= 2 kelas positif/negatif, distribusi, tuning, error analysis)                                                                                                                                                                | Side        | `P2-side-quest` | `M2`      |
| **AI Engineering** | `AI-04`  | Kurasi knowledge base tervalidasi PIC (`data/knowledge/`, metadata sumber/tanggal/versi/validasi) & ChromaDB retrieval (`Hit@3`)                                                                                                                                                     | Side        | `P1-mvp`        | `M1`      |
| **AI Engineering** | `AI-05`  | Agentic RAG (API LLM + tool calling baca-saja untuk dokumen & data sistem), prompt template + few-shot, anti prompt injection, & uji 10 pertanyaan luar konteks                                                                                                                      | Main + Side | `P1-mvp`        | `M2`      |
| **AI Engineering** | `AI-06`  | Modul AI Business Insight (SLM/LLM open-source via Modal GPU, evaluasi 10 laporan, konsistensi angka, fallback deterministik, latensi tercatat)                                                                                                                                      | Side        | `P2-side-quest` | `M3`      |
| **AI Engineering** | `AI-07`  | Integrasi kanal WhatsApp (WAHA nomor cadangan staf terdaftar / opsi Cloud API uji) & uji resiliensi kegagalan layanan AI                                                                                                                                                             | Side        | `P2-side-quest` | `M3`      |
| **DevOps / Infra** | `OPS-01` | Tata kelola Git/PR (branch `dev`, PR template `Closes #N`), GitHub Actions CI (`unit-tests` & `quality`), & secrets hygiene                                                                                                                                                          | Main + Side | `P0-blocker`    | `M1`      |
| **DevOps / Infra** | `OPS-02` | Docker Compose produksi VPS (`api`, `ai-service`, `worker`, `postgres`, `chroma`, opt-in `waha`) + reverse proxy HTTPS/TLS & isolasi port                                                                                                                                            | Main + Side | `P1-mvp`        | `M2`      |
| **DevOps / Infra** | `OPS-03` | Deployment frontend Next.js di Vercel (free tier), env server-only `API_BASE_URL`, CORS aman, & uji akses publik desktop/ponsel                                                                                                                                                      | Main + Side | `P1-mvp`        | `M2`      |
| **DevOps / Infra** | `OPS-04` | Deployment SLM/LLM open-source di Modal GPU (vLLM, Bearer auth, auto-suspend idle timeout, pantau cold-start & kredit)                                                                                                                                                               | Side        | `P2-side-quest` | `M3`      |
| **DevOps / Infra** | `OPS-05` | Penjadwalan cron sistem VPS untuk worker, backup otomatis Postgres/Chroma, & uji failover/anti-duplikasi pra-demo                                                                                                                                                                    | Side        | `P2-side-quest` | `M4`      |

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

| Milestone                                    | Rentang Waktu     | Target Utama                                                                                                                                                                              | Issue Terkait                                                                     |
| -------------------------------------------- | ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| **M1 — Rancangan Disepakati**                | 21–27 Nov 2026    | Konfirmasi PIC, baseline waktu manual, mockup, skema DB, kontrak API, dataset awal + kamus data, konfigurasi ChromaDB, CI & uji kelayakan layanan                                         | `FS-01`, `FS-02`, `FS-03`, `DS-01`, `DS-03`, `AI-01`, `AI-04`, `OPS-01`           |
| **M2 — Fitur Inti Tersedia**                 | 28 Nov–4 Des 2026 | Katalog menu/resep & hitung bahan, input pesanan & jadwal, EDA 5 pertanyaan, model relevansi 2 kelas, forecasting MA vs RF, model sentimen, Agentic RAG, VPS Compose & Vercel             | `FS-04`, `FS-05`, `DS-02`, `DS-04`, `AI-02`, `AI-03`, `AI-05`, `OPS-02`, `OPS-03` |
| **M3 — Alur Utama Selesai & Feature Freeze** | 5–11 Des 2026     | Invoice digital + DP/pelunasan + PDF, integrasi Chat AI & Dasbor Analitik (upload + prediksi + insight PDF), serving forecasting, SLM Modal GPU, WAHA uji; **Feature Freeze 11 Des 2026** | `FS-06`, `FS-07`, `FS-08`, `DS-05`, `AI-06`, `AI-07`, `OPS-04`                    |
| **M4 — Validasi & Finalisasi**               | 12–20 Des 2026    | Pengujian 20 skenario, cron worker & failover, audit akurasi data akhir, demo skenario **100 nasi box** bersama PIC, ukur waktu sistem vs baseline, bugfix, README & user manual          | `FS-09`, `DS-06`, `OPS-05`                                                        |

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
  1. Transport autentikasi web BFF (`HttpOnly cookie` vs `Authorization: Bearer`) dan durasi sesi.
  2. Provider proprietary LLM API (Gemini vs OpenAI), model embedding (lokal multilingual vs API), bobot SLM Modal GPU (`Qwen2.5-7B-Instruct` vs `Llama-3.2-3B`), serta kredensial SMTP email.
  3. Aktivasi opsional ekstensi >= 4 kelas intent (`POST /api/v1/ml/predict-intent`) apabila jadwal sebelum feature freeze mencukupi.
  4. Domain/subdomain VPS untuk TLS dan batas tanggal _chronological holdout split_ forecasting.

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
