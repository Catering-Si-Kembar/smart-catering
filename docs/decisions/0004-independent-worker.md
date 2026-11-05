# ADR-0004: Worker Mandiri Always-On dengan Liveness Internal Tanpa Ketergantungan API/AI

**Tanggal:** 2026-11-04 · **Status:** accepted · **Diperbarui:** 2026-11-05

**Pengambil keputusan:** pemilik proyek; diperbarui untuk menegaskan pembedaan liveness internal worker dari kontrak REST publik API/AI service.

## Konteks

Pekerjaan background masa depan membutuhkan proses yang tidak terikat request lifecycle `apps/api` maupun `apps/ai-service`. Ketika `apps/api` dan `apps/ai-service` mengadopsi envelope REST `{ data, meta: { requestId } }` serta dokumentasi OpenAPI 3.1/Scalar, perlu ditetapkan apakah `apps/worker` ikut menjadi backend REST berdokumentasi atau tetap menjadi proses worker internal murni.

## Keputusan

1. **Proses Node.js Mandiri**:
   - Worker adalah aplikasi Node.js terpisah di `apps/worker/src`, dibangun dengan TypeScript ke ESM (`dist/index.js`) dan dapat start/restart tanpa `apps/api` maupun `apps/ai-service`.
   - Dependency awal hanya `@smart-catering/types` (`db` baru dipakai ketika ada job yang membutuhkan DB). Worker tidak boleh mengimpor `apps/api` atau `apps/ai-service`.
2. **Kontrak Liveness Internal Mentah (`HealthData`)**:
   - Worker **bukan** salah satu dari dua backend REST aplikasi, sehingga tidak memiliki OpenAPI/Scalar (`/docs`) dan tidak menggunakan envelope `{ data, meta }`.
   - Worker membuka HTTP `GET /health` pada `127.0.0.1:3002` lokal (`0.0.0.0:3002` di jaringan container internal VPS saja) dan mengembalikan tipe `HealthData` mentah `{"status":"ok","service":"worker"}`; path lain mengembalikan `404` dan method selain `GET` pada `/health` mengembalikan `405`.
   - Menutup server secara bersih pada sinyal `SIGINT`/`SIGTERM`.
3. **Isolasi Rahasia dan Kredensial**:
   - Pada Fase 0, worker hanya menerima `NODE_ENV`, `WORKER_HOST`, dan `WORKER_PORT`. Worker tidak menerima `DATABASE_URL`, `WAHA_API_KEY`, `CHROMA_URL`, `AI_SERVICE_URL`, maupun `DOCS_ENABLED`/`DOCS_USERNAME`/`DOCS_PASSWORD`.
   - Redis + BullMQ hanya opsi evolusi bila queue dibutuhkan kelak; tidak di-install, dikonfigurasi, atau dikonsumsi pada Fase 0. Tidak ada integrasi Telegram.

## Alternatif yang dipertimbangkan

- **Menjadikan worker sebagai backend REST ketiga dengan Scalar/OpenAPI:** menambah kompleksitas dan permukaan dokumentasi pada proses internal yang hanya mengeksekusi background job dan healthcheck container; ditolak.
- **Job di Route Handler API atau FastAPI background task:** mengikat lifecycle job ke proses HTTP request/restart; ditolak.

## Konsekuensi

**Positif:** lifecycle, build image, dan pengujian worker tetap sangat ringan dan terisolasi dari perubahan lapisan REST/OpenAPI maupun kredensial layanan lain.

**Biaya:** konsumen tipe di `@smart-catering/types` membedakan `HealthData` (`{ status: 'ok', service }`, dipakai langsung oleh worker) dari `HealthResponse` (`ApiSuccess<HealthData>`, dipakai oleh `api` dan `ai-service`).

## Rujukan

[Development](../development.md) · [Arsitektur](../architecture.md) · [PRD v2.2](../PRD_FASE_0.md) · [Indeks ADR](README.md)
