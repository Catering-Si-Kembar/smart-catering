# ADR-0005: Migrasi Backend API ke Express, Joi, dan Rute `/api/v1` serta Penyelarasan Ruang Kerja Tim

**Tanggal:** 2026-11-23 · **Status:** accepted

**Pengambil keputusan:** tim arsitek dan pengembang platform; diselaraskan untuk kebutuhan pengembangan backend operasional, kejelasan validasi skema, ekspansi modul katering, dan pembagian ruang kerja tim.

## Konteks

Pada fondasi awal Fase 0, `apps/api` dibangun di atas Next.js Route Handlers dengan validasi skema Zod dan layout direktori `apps/api/app/`. Pendekatan tersebut menimbulkan sejumlah tantangan operasional dan teknis saat mempersiapkan implementasi fitur katering komprehensif:

1. **Framework Overhead & Runtime:** Next.js dioptimalkan terutama untuk frontend dan fullstack web yang melibatkan rendering React. Menjalankan service API murni di lingkungan VPS dalam mode server standalone menambahkan overhead build, kompleksitas siklus hidup, dan abstraksi framework yang tidak diperlukan oleh backend REST murni.
2. **Kebutuhan Routing Middleware & Ekosistem:** Express 5 menyediakan middleware pipeline yang teruji (`cors`, `helmet`, rate limiting, router modular per domain bisnis), penanganan error terpusat yang fleksibel, serta kemudahan pengujian HTTP server secara langsung.
3. **Standarisasi Validasi Schema:** Joi 18.3.2 menawarkan deklarasi validasi objek yang kuat, ekspresif, dan berkinerja tinggi untuk memvalidasi payload request kompleks (body, query, params) tanpa ketergantungan pada runtime compiler TypeScript khusus.
4. **Cakupan Domain Bisnis MVP:** Modul `inventory` dihapus dari cakupan MVP karena operasional Catering Si Kembar lebih memprioritaskan katalog menu, resep, kalkulator bahan baku (`menus`), manajemen pesanan (`orders`), pencatatan keuangan (`finance`), analitik penjualan (`analytics`), modul interaksi pengguna (`chat`, `reminders`), serta integrasi notifikasi (`integrations/email` dan `integrations/waha`).
5. **Kebutuhan Ruang Kerja Tim:** Kolaborasi tim multi-disiplin membutuhkan direktori kerja khusus yang terisolasi untuk data riset dan kamus bahan (`data/`), eksperimen pemodelan data (`notebooks/`), artefak deployment SLM AI Business Insight (`infra/modal/`), serta spesifikasi teknis issue terstruktur (`docs/spec/`).

## Keputusan

1. **Migrasi `apps/api` ke Express 5 & TypeScript:**
   - Menggunakan Express 5.3.0 dengan TypeScript di `apps/api/src/` yang dikompilasi menjadi ESM ke `dist/src/index.js`.
   - Menggunakan `cors` dan `helmet` untuk pengamanan dasar HTTP transport.
   - Mengadopsi base path `/api/v1` untuk seluruh endpoint bisnis dan health API (`/health` dan `/api/v1/health`), serta menyediakan dokumentasi interaktif di `/docs` dan skema mentah di `/api/openapi`.
2. **Validasi Request dengan Joi 18.3.2:**
   - Seluruh validasi skema HTTP (body, query, params) menggunakan Joi 18.3.2.
   - Error validasi dipetakan secara seragam ke format RFC 9457 `application/problem+json` dengan status 422 dan korelasi UUID request ID kanonis.
3. **Pemetaan Ulang Modul Bisnis & Boundary Layanan:**
   - Menghapus modul `inventory` dari cakupan `apps/api`.
   - Menetapkan modul bisnis transaksional di `apps/api/modules/{auth,menus,orders,finance,analytics,chat,reminders}/` dan integrasi di `apps/api/integrations/{waha,email}/`.
   - Menetapkan boundary `apps/ai-service` di `apps/ai-service/app/{rag,chroma,insight,ml/{relevance,forecasting,sentiment}}/`.
4. **Penyelarasan Ruang Kerja Tim:**
   - Menambahkan ruang kerja tim: `data/{raw,synthetic,knowledge,dictionary}/`, `notebooks/`, `infra/modal/`, dan `docs/spec/` (termasuk paket 27 spesifikasi issue di `docs/spec/issues/`).
5. **Pemeliharaan Kontrak Wire REST & Scalar OpenAPI 3.1.0:**
   - Mempertahankan 100% kontrak envelope `{ data, meta: { requestId } }`, RFC 9457 Problem Details, header `X-Request-Id`, helper paginasi, helper 204, serta Scalar UI fail-closed di produksi.

## Alternatif yang dipertimbangkan

- **Mempertahankan Next.js Route Handlers + Zod:** Menghasilkan waktu build container yang lebih lambat, mewajibkan konvensi file routing Next.js (`app/**/route.ts`), serta mencampur aduk paradigma web dengan REST backend murni; ditolak.
- **Fastify:** Alternatif performa tinggi, namun ekosistem middleware dan kemudahan adopsi tim lebih condong ke Express 5; ditolak.
- **Mempertahankan modul `inventory` di Fase 0/1:** Kebutuhan aktual mitra saat ini lebih fokus pada kalkulasi bahan baku per pesanan menu daripada sistem inventaris gudang penuh; ditolak.

## Konsekuensi

**Positif:**

- Build dan runtime `apps/api` jauh lebih ringan, cepat, dan standar Node.js murni (`node dist/src/index.js`).
- Routing Express lebih fleksibel untuk sub-router modular per domain bisnis di `/api/v1`.
- Skema validasi Joi terpusat, konsisten, dan mudah diintegrasikan dengan generator spesifikasi OpenAPI 3.1.0.
- Ruang kerja tim menjadi tertata rapi untuk data engineering, machine learning notebooks, dan spesifikasi issue.

**Biaya:**

- `apps/api` menggunakan layout `src/` (`apps/api/src/`), berbeda dari `apps/web/app/`.
- Perlu sinkronisasi dokumentasi arsitektur, struktur repository, dan panduan development.

## Rujukan

[Development](../development.md) · [Arsitektur](../architecture.md) · [Struktur Repository](../repository-structure.md) · [Spesifikasi Teknis](../spec/README.md) · [Indeks ADR](README.md)
