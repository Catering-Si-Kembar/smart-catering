# Changelog

Perubahan bermakna dicatat di sini. Entri fondasi bukan klaim rilis/deployment atau kelulusan pemeriksaan yang belum diamati.

## [Unreleased] — 2026-11-05

### Ditambahkan

- Workspace keenam `@smart-catering/ai-service` (`apps/ai-service`) berbasis Python **3.12** (`>=3.12,<3.14`), **uv 0.13.7**, FastAPI **0.162.0**, Pydantic **2.14.2**, Uvicorn **0.54.0**, `scalar-fastapi` **1.9.1**, dan `python-dotenv` **1.2.4** pada port internal `8001`, dilengkapi wrapper `package.json` tanpa dependency Node agar terintegrasi dengan npm Workspaces dan Turborepo.
- Deklarasi optional extras Python pada `apps/ai-service/pyproject.toml` untuk fase mendatang: `rag` (`langchain==1.4.8`, `chromadb==1.5.9`) dan `ml` (`scikit-learn==1.9.1`), terkunci di `apps/ai-service/uv.lock` namun tidak di-install secara default pada `npm run ai:sync` maupun image produksi.
- Kontrak wire REST bersama di `@smart-catering/types`, `@smart-catering/api`, dan `@smart-catering/ai-service`:
  - Envelope sukses `200`/`201` `{ data, meta: { requestId, pagination? } }` dan helper `204 No Content` tanpa body.
  - Penanganan error standar RFC 9457 (`application/problem+json`) untuk `400`, `401`, `403`, `404`, `405`, `422` (`Unprocessable Content` beserta array `errors: [{ path, code, message }]`), dan `500` teredaksi (`"An unexpected error occurred."`).
  - Propagasi dan generasi UUID kanonis melalui header `X-Request-Id` dan metadata respons.
  - Helper dan validasi paginasi reusable (`page`, `limit`, `total`, `totalPages`) dengan batas integer aman `9007199254740991` dan pencegahan overflow offset yang selaras antara TypeScript dan Python.
- Dokumentasi OpenAPI **3.1.0** dan UI Scalar API Reference (bundle klasik dipin ke `https://cdn.jsdelivr.net/npm/@scalar/api-reference@1.76.4`, tanpa AI agent/telemetry/remote proxy/font eksternal) pada kedua backend:
  - `@smart-catering/api`: `GET /docs` dan `GET /api/openapi` (menggunakan `zod@4.6.7`, `@asteasolutions/zod-to-openapi@9.1.0`, `@scalar/nextjs-api-reference@0.12.15`).
  - `@smart-catering/ai-service`: `GET /docs` dan `GET /openapi.json` (menggunakan FastAPI OpenAPI 3.1.0 dan `scalar-fastapi@1.9.1`).
- Gerbang keamanan dokumentasi produksi (`DOCS_ENABLED`, `DOCS_USERNAME`, `DOCS_PASSWORD`): aktif default di development/test, nonaktif default (`404` Problem Details) di produksi, fail-closed (`500` Problem Details) bila diaktifkan di produksi tanpa password minimal 32 karakter, serta dilindungi HTTP Basic Auth constant-time (`401` Problem Details + `WWW-Authenticate`) dengan `Cache-Control: private, no-store` dan `Vary: Authorization`.
- `infra/docker/ai-service.Dockerfile` non-root berbasis `python:3.12.16-slim-bookworm@sha256:e697c81897302a4c4333bade000d98038fbb21eb064f8ee1fd42d02ebcd9d337` dan `uv==0.13.7` (`uv sync --frozen --no-dev`), serta service internal `ai-service` pada `infra/docker/compose.vps.yaml` tanpa publikasi port host.
- Launcher layanan dan isolasi environment dua sumber (`scripts/service-environment.mjs`, `scripts/run-service.mjs`) beserta root scripts baru: `ai:sync`, `dev:backend`, `dev:ai`, `start:all`, `start:backend`, `start:ai`, serta perluasan `dev:all`, `test`, `test:coverage`, `format`, `format:check`, `smoke`, dan workflow CI untuk mencakup workspace Python.
- Infografik arsitektur Smart Catering pada `docs/assets/smart-catering-architecture.svg` dan PNG 2000 × 2570, ditautkan dari dokumentasi arsitektur. Diagram membedakan fondasi Fase 0, integrasi yang belum aktif, target deployment Vercel/VPS, enam workspace, serta CI khusus `dev`.
- Logo resmi Katering Si Kembar pada `docs/assets/logo-katering-si-kembar.png`, disalin tanpa mengubah desain dari aset yang diberikan mitra.

### Diubah

- Konsolidasi arsitektur environment dari enam file `.env` menjadi tepat **dua sumber `.env` aktif**: root `.env` (`.env.example` → `.env`) untuk backend (`api`, `ai-service`, `worker` melalui allowlist per layanan), Prisma CLI (`DATABASE_URL`), dan interpolasi Docker Compose, serta `apps/web/.env` (`apps/web/.env.example` → `apps/web/.env`) khusus frontend (`NEXT_PUBLIC_APP_NAME` dan `API_BASE_URL`). Template lama di `apps/api`, `apps/ai-service`, `apps/worker`, dan `packages/db` dihapus tanpa fallback warisan.
- README diperkaya sebagai dokumentasi proyek Capstone **Asah led by Dicoding** bersama mitra **Katering Si Kembar**, dilengkapi header logo terpusat, badge metadata terverifikasi, navigasi cepat beserta tautan `Changelog` / `Report Bug` / `Request Feature`, visi lima pilar produk dibanding batas jujur Fase 0, panduan setup dua file `.env`, command `dev:all`/`dev:web`/`dev:backend`/`start:all`/`start:backend`/individual, serta bagian tim kontributor dan pelaporan isu.
- Tautan repository, laporan bug/fitur, pull request, dan kontributor diarahkan ke repository GitHub resmi yang bersifat private; file crash shell lokal (`*.stackdump`) dikecualikan dari publikasi Git.
- Kepemilikan boundary RAG, ML, dan Chroma dipindahkan sepenuhnya dari `apps/api` ke `apps/ai-service/app/{rag,ml,chroma}/README.md`. Direktori placeholder lama `apps/api/modules/rag`, `apps/api/modules/ml`, dan `apps/api/integrations/chroma` dihapus; `apps/api` kini menyimpan `AI_SERVICE_URL` untuk komunikasi internal masa depan, sementara `CHROMA_URL` dimiliki oleh `apps/ai-service`. Boundary `apps/api/integrations/waha` tetap di Node API.
- Respons `GET /health` pada `@smart-catering/api` (`:3001/health`) diperbarui menggunakan envelope standar `{"data":{"status":"ok","service":"api"},"meta":{"requestId":"<uuid>"}}`. `@smart-catering/worker` (`:3002/health`) tetap mempertahankan respons liveness internal `{"status":"ok","service":"worker"}` (`HealthData`) dan tidak menerima kredensial database, provider, maupun dokumentasi.
- Tahap `deps` pada `infra/docker/api.Dockerfile` dan `infra/docker/worker.Dockerfile` menyalin `apps/ai-service/package.json` agar `npm ci` mengenali keenam workspace di `package-lock.json` tanpa memasang Python di image Node.
- Dokumentasi README, PRD Fase 0 v2.2, arsitektur, struktur repository, environment, development, deployment VPS/Vercel, ADR 0001–0004, dan rencana implementasi diperbarui di tempat (in-place) agar selaras dengan arsitektur enam workspace.
- OpenAPI FastAPI diturunkan dari route yang terdaftar, kemudian diperkaya komponen kontrak bersama; OpenAPI Next memakai tipe native OpenAPI 3.1 dan mendokumentasikan input opsional `X-Request-Id` pada health.
- Test client Python menggunakan `httpx2` agar sesuai dengan Starlette. Uvicorn dijalankan dengan `--no-access-log` untuk menghindari pencatatan query sensitif; logging error teredaksi tetap aktif.
- Penanganan input mempertahankan key query khusus seperti `__proto__`, membatasi integer paginasi sebelum konversi, dan menjaga identitas UTF-8 kredensial dokumentasi. Favicon default eksternal Scalar FastAPI dinonaktifkan.

---

## [Fase 0 Baseline] — 2026-11-04

### Ditambahkan

- Fondasi Smart Catering Hybrid Minimal Monorepo awal dengan lima workspace private: web, API, worker, db, dan types; npm Workspaces, Turbo, satu lockfile root, dan tooling strict.
- Kontrak landing setup, API health awal, serta worker independen dengan HTTP liveness dan graceful shutdown, tanpa fitur bisnis/job aktif.
- Prisma lazy server-only dengan schema tanpa model bisnis, PostgreSQL biasa, Chroma terpisah, serta WAHA opt-in tanpa sesi/pengiriman pesan.
- Konfigurasi Compose dev/VPS dan Dockerfile API/worker non-root, CI development serta unit coverage khusus validasi environment worker dan smoke built proses aplikasi.
- Dokumentasi Indonesia: onboarding, struktur source, development, environment, architecture, deployment web-only Vercel/VPS, PRD Fase 0 v2.1, serta ADR pengganti.

### Diubah

- Rencana awal satu-satunya file repository diganti dengan rencana implementasi hybrid yang diterima. Tidak ada source pnpm yang dimigrasikan.
- Asumsi lama sebelas workspace, dua Vercel, worker lokal saja, pgvector, shared RAG/ML/UI/services/config diganti arsitektur hybrid minimal, backend always-on VPS, serta Chroma terpisah.
- Penamaan command infra memakai `infra:up`, `infra:down`, `infra:config`, `infra:waha`; Prisma memakai `db:generate`/`db:validate`.
- Penyederhanaan source Next telah disetujui: `apps/web/app` dan `apps/api/app` langsung pada root workspace tanpa `src`; worker dan packages tetap mempertahankan `src`.
- File `.gitkeep` dihapus; README batas modul tetap dipertahankan.
- npm12 `allowScripts` root menyetujui hanya `prisma@7.10.1`, `@prisma/engines@7.10.1`, dan `esbuild@0.28.2` secara exact tanpa blanket approval; ESLint dipin 9.39.5 agar sesuai plugin Next.
- Compose VPS memakai `VPS_DATABASE_URL` internal lengkap untuk API, bukan concatenation password mentah.
- `next-env.d.ts` diperlakukan sebagai output generator Next dan diabaikan Git/formatter.

### Batas scope dan bukti

- Belum ada autentikasi pengguna bisnis, CRUD bisnis, pipeline RAG/ML aktif, training model, reminder, queue, integrasi Telegram, atau pengiriman WhatsApp. Redis + BullMQ hanya opsi arsitektur masa depan dan tidak di-install.
- Docker Engine tidak tersedia pada lingkungan lokal yang diaudit sebelumnya. Validasi model Compose offline berbeda dari image build/start, query DB, dan health/persistensi dependency runtime.
- Hasil install/build/lint/typecheck/test/coverage/smoke, CI remote, serta deployment hanya boleh dinyatakan berdasarkan output aktual pelaksana integrasi. Rincian keterbatasan dan bukti yang telah diterima ada di [indeks dokumentasi](docs/README.md#status-dan-batas-bukti).
