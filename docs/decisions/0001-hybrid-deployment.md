# ADR-0001: Web di Vercel; API, AI Service, Worker, dan Infrastruktur di VPS

**Tanggal:** 2026-11-04 · **Status:** accepted · **Diperbarui:** 2026-11-05

**Pengambil keputusan:** pemilik proyek melalui scope hybrid yang diterima; diperbarui pada penambahan layanan Python AI dan standar REST/OpenAPI Fase 0.

## Konteks

Frontend memperoleh manfaat deployment Next.js di Vercel, sedangkan API, layanan AI Python/FastAPI, worker background, database, vector store, dan layanan messaging membutuhkan lifecycle always-on serta jaringan internal yang dikelola bersama. Rencana awal menyebut dua project Vercel dan worker lokal saja; keputusan terbaru menggantinya dengan topologi hybrid terpusat di VPS untuk seluruh layanan backend.

## Keputusan

1. **Pemisahan Vercel vs VPS**:
   - Deploy hanya `apps/web` ke satu project Vercel.
   - Deploy `apps/api` (Next.js standalone `:3001`), `apps/ai-service` (Python 3.12 / FastAPI / Uvicorn `:8001` dikelola `uv`), dan `apps/worker` (Node.js independen `:3002`) secara always-on di VPS bersama PostgreSQL (`:5432`) dan Chroma (`:8000`); WAHA (`:3000`) tetap profile opt-in.
2. **Isolasi Jaringan VPS**:
   - Hanya `api` yang dipetakan ke loopback host VPS (`127.0.0.1:3001`) di belakang reverse proxy TLS eksternal.
   - `ai-service`, `worker`, PostgreSQL, Chroma, dan WAHA tidak memiliki host port pada VPS dan hanya dapat dijangkau melalui jaringan container internal (`smart_catering_vps_net`).
   - `api` menyimpan `AI_SERVICE_URL` (`http://ai-service:8001` di VPS) sebagai konfigurasi komunikasi internal masa depan tanpa panggilan aktif atau ketergantungan startup pada Fase 0.
3. **Gerbang Keamanan Dokumentasi OpenAPI 3.1 & Scalar di Produksi**:
   - Kedua backend (`api` dan `ai-service`) menyediakan dokumentasi Scalar (`/docs`) dan skema OpenAPI 3.1.0 (`/api/openapi` pada API, `/openapi.json` pada AI service).
   - Di lingkungan produksi (`NODE_ENV=production` / `APP_ENV=production`), `DOCS_ENABLED` bernilai default **`false`** (mengembalikan `404` Problem Details).
   - Jika diaktifkan di produksi (`DOCS_ENABLED=true`), akses wajib dilindungi HTTP Basic Auth constant-time dengan `DOCS_USERNAME` dan `DOCS_PASSWORD` (minimal 32 karakter) di balik reverse proxy TLS/HTTPS, serta header `Cache-Control: private, no-store` dan `Vary: Authorization`. Misconfig kredensial produksi gagal tertutup (`500` Problem Details generik).

## Alternatif yang dipertimbangkan

- **Dua project Vercel ( atau men-deploy API/AI ke serverless Vercel):** menyulitkan koneksi internal ke PostgreSQL, Chroma, dan WAHA serta membatasi runtime Python/worker always-on; tidak dipilih.
- **Mempublikasikan port `ai-service` (`:8001`) langsung ke internet:** memperluas permukaan serangan tanpa kebutuhan karena browser/frontend berkomunikasi melalui `api`; ditolak, `ai-service` tetap internal.

## Konsekuensi

**Positif:** lifecycle frontend dan backend jelas; layanan AI Python, data, vector store, dan messaging terisolasi di jaringan internal VPS; dokumentasi OpenAPI produksi aman secara default (fail-closed).

**Biaya:** operator wajib mengelola VPS, reverse proxy/TLS, firewall, backup, patch, dan pemantauan untuk container Node dan Python.

## Rujukan

[Arsitektur](../architecture.md) · [Vercel](../deployment-vercel.md) · [VPS](../deployment-vps.md) · [Indeks ADR](README.md)
