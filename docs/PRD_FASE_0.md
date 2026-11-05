# PRD Fase 0 — Smart Catering

**Versi:** 2.2 · **Diperbarui:** 2026-11-05 · **Status scope:** diterima

## 1. Kedudukan dokumen

PRD ini menormalkan keputusan terbaru pengguna untuk **Hybrid Minimal Monorepo** enam workspace dengan fondasi kontrak REST/OpenAPI 3.1 dan layanan AI Python/FastAPI (`uv`). Ia menggantikan ketentuan yang bertentangan dalam rencana awal (dua project Vercel, worker lokal saja, sebelas workspace, pgvector, paket shared RAG/ML terpisah) sekaligus memperbarui baseline lima workspace sebelumnya yang belum menyertakan layanan Python AI dan standar envelope REST/OpenAPI. Dokumen ini **bukan salinan verbatim** file PRD di luar repository yang tidak tersedia sebagai source terverifikasi.

Audit awal hanya menemukan satu file rencana, `docs/superpowers/plans/2026-11-04-fase-0-setup-monorepo.md`. Tidak ada source aplikasi, npm/pnpm workspace atau lockfile untuk dimigrasikan. Implementasi Fase 0 membangun fondasi baru; menyebutnya migrasi source pnpm adalah tidak tepat. Rencana pada path yang sama telah diperbarui agar selaras dengan versi 2.2 ini.

## 2. Tujuan dan pengguna

Tujuan Fase 0 adalah fondasi yang dapat dipasang dari clean checkout menggunakan `npm` dan `uv`, dijalankan lokal pada empat proses aplikasi (`web`, `api`, `ai-service`, `worker`), menerapkan kontrak wire REST/OpenAPI 3.1.0 + Scalar API Reference yang konsisten dan aman pada kedua backend (`api` dan `ai-service`), diperiksa melalui tooling lintas bahasa, serta disiapkan untuk deployment hybrid tanpa membangun fitur bisnis. Pengguna langsung fase ini adalah developer dan operator yang membutuhkan boundary, kontrak HTTP, command, env, dan konfigurasi deployment yang jelas.

Smart Catering ditujukan untuk pengelolaan katering pada fase berikutnya. Pada Fase 0 belum tersedia alur pelanggan, operasional pesanan/stok/keuangan, autentikasi pengguna bisnis, atau pipeline AI/RAG/ML aktif. Landing setup bukan dashboard bisnis.

## 3. Scope dan non-goals

### Termasuk

- Tepat **enam workspace private** dengan versi `0.0.0`: `@smart-catering/web`, `@smart-catering/api`, `@smart-catering/ai-service`, `@smart-catering/worker`, `@smart-catering/db`, dan `@smart-catering/types`.
- npm Workspaces (`apps/*`, `packages/*`) dengan satu root `package-lock.json` untuk ekosistem Node.js, serta **uv 0.13.7** dengan `apps/ai-service/pyproject.toml`, `apps/ai-service/uv.lock`, dan `.python-version` (`3.12`) untuk ekosistem Python (`@smart-catering/ai-service` memiliki `package.json` khusus task wrapper tanpa dependency Node).
- Web Next.js App Router di `apps/web/app` tanpa `src`, port 3000, metadata/branding Smart Catering, CSS biasa, tanpa remote font wajib build.
- API Next.js Route Handlers di `apps/api/app` tanpa `src`, port 3001, output standalone untuk VPS, melayani `GET /health` (beserta `HEAD /health`), `GET /docs`, `GET /api/openapi`, serta catch-all `404`/`405` terstandarisasi dan helper kontrak di `apps/api/lib/`.
- AI Service Python/FastAPI di `apps/ai-service/app` (layout flat tanpa `src`), port internal 8001, melayani `GET /health` (beserta `HEAD /health`), `GET /docs`, `GET /openapi.json`, serta exception handlers RFC 9457, helper validasi/paginasi, dan README boundary `app/rag/`, `app/ml/`, serta `app/chroma/`.
- Deklarasi optional dependency extras pada `apps/ai-service/pyproject.toml`: `rag` (`langchain==1.4.8`, `chromadb==1.5.9`) dan `ml` (`scikit-learn==1.9.1`), terkunci dalam `uv.lock` tetapi **tidak** di-install pada sinkronisasi default maupun image produksi.
- Kontrak wire REST bersama untuk `@smart-catering/api` dan `@smart-catering/ai-service`: envelope sukses `{ data, meta: { requestId, pagination? } }`, helper `204 No Content`, error RFC 9457 `application/problem+json` (`400`, `401`, `403`, `404`, `405`, `422 Unprocessable Content` dengan `errors: [{ path, code, message }]`, `500` teredaksi), korelasi `X-Request-Id` UUID kanonis, helper paginasi reusable, dan gerbang keamanan dokumentasi `DOCS_ENABLED` / `DOCS_USERNAME` / `DOCS_PASSWORD`.
- Worker Node.js independen di 3002 untuk liveness internal (`{"status":"ok","service":"worker"}`) dan graceful shutdown, tanpa job/scheduler aktif.
- Shared types di `@smart-catering/types` dan Prisma client lazy di `@smart-catering/db` tanpa model bisnis; PostgreSQL biasa dan Chroma terpisah melalui Compose.
- Arsitektur environment dua sumber: root `.env` (`.env.example` → `.env`) sebagai sumber terpusat backend (`api`, `ai-service`, `worker`), Prisma CLI, dan Docker Compose yang disaring ketat berdasarkan allowlist layanan, serta `apps/web/.env` (`apps/web/.env.example` → `apps/web/.env`) khusus frontend tanpa file `.env` tambahan di workspace backend.
- WAHA opt-in sebagai infrastruktur internal yang dinonaktifkan secara default, tanpa sesi/login/pengiriman pesan.
- Dockerfile non-root untuk `api`, `ai-service`, dan `worker`; Compose dev/VPS; CI development Node + Python; serta dokumentasi setup/operasi Bahasa Indonesia yang jujur.

### Tidak termasuk

Autentikasi/otorisasi pengguna bisnis (JWT/session login), CRUD dan schema bisnis, endpoint bisnis tiruan semata-mata untuk contoh paginasi/204, dashboard/login palsu, chatbot/RAG aktif, pemanggilan LLM, embedding/retrieval Chroma aktif, training/inference model ML, pengiriman WhatsApp, reminder, cron/job aktif, integrasi Telegram, instalasi Redis/BullMQ, dan package shared tambahan (`packages/ui`, `rag`, `ml`, `services`, `config`). Deployment cloud, provisioning VPS/domain, push remote, dan branch protection tidak diklaim terlaksana hanya karena konfigurasinya ditulis.

## 4. Arsitektur yang diterima

| Workspace                    | Tanggung jawab                                                                                   | Target runtime                         |
| ---------------------------- | ------------------------------------------------------------------------------------------------ | -------------------------------------- |
| `@smart-catering/web`        | Landing/setup frontend, future server-side fetch API                                             | Vercel saja                            |
| `@smart-catering/api`        | REST backend utama (`/health`, `/docs`, `/api/openapi`), modul bisnis & integrasi WAHA           | VPS always-on (loopback `:3001` → TLS) |
| `@smart-catering/ai-service` | REST backend AI (`/health`, `/docs`, `/openapi.json`), owner boundary RAG, ML, dan Chroma        | VPS always-on (internal `:8001` saja)  |
| `@smart-catering/worker`     | Liveness proses background internal (`:3002`); future jobs terpisah                              | VPS always-on, mandiri dari API & AI   |
| `@smart-catering/db`         | Prisma schema/config dan lazy `getDb()`                                                          | Server Node saja                       |
| `@smart-catering/types`      | Shared TypeScript contract (`HealthData`, `ApiSuccess`, `ProblemDetails`, `PaginationMeta`, dll) | Shared compile-time contract           |

Dependency internal Node memakai versi exact `0.0.0`, bukan `workspace:*`. `db` dan `types` dibangun ke `dist` ESM dengan declarations. API bergantung pada `db`/`types`; worker awalnya hanya `types` dan tidak boleh mengimpor `apps/api` maupun `apps/ai-service`. `apps/ai-service` adalah layanan Python terpisah yang tidak mengimpor internal `apps/api`. Web tidak boleh mengimpor DB atau integrasi server.

Kepemilikan modul dan integrasi:

- `apps/api/modules/{auth,orders,inventory,finance}` dan `apps/api/integrations/waha`: boundary bisnis dan WhatsApp milik Node API. Direktori lama `apps/api/modules/{rag,ml}` dan `apps/api/integrations/chroma` **dihapus** karena kepemilikannya berpindah ke `apps/ai-service`.
- `apps/ai-service/app/{rag,ml,chroma}`: boundary RAG, ML, dan vector store Chroma milik layanan Python AI.
- `apps/api` memiliki konfigurasi `AI_SERVICE_URL` (`http://127.0.0.1:8001` lokal, `http://ai-service:8001` di VPS) untuk pemanggilan internal masa depan tanpa ketergantungan startup atau pemanggilan aktif pada Fase 0. `CHROMA_URL` dimiliki oleh `apps/ai-service`.

VPS menyimpan `ai-service` (`:8001`), `worker` (`:3002`), PostgreSQL (`:5432`), Chroma (`:8000`), dan WAHA (`:3000`) pada jaringan container internal tanpa port host. Hanya `api` dipetakan ke loopback host `127.0.0.1:3001` di belakang reverse proxy TLS eksternal.

## 5. Persyaratan fungsional

| ID    | Persyaratan                                                                                                                                                                                                                                                           |
| ----- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| FR-01 | Clean install Node dari root melalui `npm ci` (satu `package-lock.json`, enam workspace) dan sinkronisasi Python melalui `npm run ai:sync` (`uv sync --project apps/ai-service --frozen` dari `uv.lock`)                                                              |
| FR-02 | Web `/` menampilkan identitas Smart Catering dan status setup, bukan fitur bisnis palsu                                                                                                                                                                               |
| FR-03 | API `GET /health` (`:3001`) dan AI Service `GET /health` (`:8001`) mengembalikan HTTP 200 `{"data":{"status":"ok","service":"api"\|"ai-service"},"meta":{"requestId":"<uuid>"}}` tanpa koneksi DB/Chroma                                                              |
| FR-04 | Worker `GET /health` (`:3002`) mengembalikan HTTP 200 liveness internal `{"status":"ok","service":"worker"}` (`HealthData` tanpa wrapper `data`/`meta`); path lain 404, method selain GET 405; graceful shutdown                                                      |
| FR-05 | `@smart-catering/types` mengekspor `HealthService` (`'api' \| 'worker' \| 'ai-service'`), `HealthData`, `ApiMeta`, `PaginationMeta`, `ApiSuccess<T>`, `HealthResponse`, `ValidationIssue`, `ProblemDetails`                                                           |
| FR-06 | Kedua backend (`api` dan `ai-service`) menyediakan helper `200`/`201` (`{ data, meta }`), helper `204 No Content` (body kosong, tanpa JSON `Content-Type`, tetap `X-Request-Id`), serta dukungan `HEAD` tanpa body                                                    |
| FR-07 | Kedua backend mengembalikan error RFC 9457 `application/problem+json` untuk `400`, `401`, `403`, `404`, `405`, `422` (judul `Unprocessable Content` + `errors: [{ path, code, message }]`), dan `500` teredaksi                                                       |
| FR-08 | Korelasi `X-Request-Id` menerima UUID RFC kanonis (v1–v8) yang dinormalisasi ke lowercase, atau membuat UUIDv4 baru jika hilang/tidak valid; selalu dikembalikan di header `X-Request-Id` dan body JSON                                                               |
| FR-09 | Helper/model paginasi reusable (`page` default 1, `limit` default 20 max 100, `total` safe integer `<= 9007199254740991`, `totalPages`) menolak boolean, pecahan, negatif, unsafe integer, dan overflow offset                                                        |
| FR-10 | OpenAPI `3.1.0` mentah (`/api/openapi` di API, `/openapi.json` di AI service) dan UI Scalar (`/docs` dengan bundle klasik `@scalar/api-reference@1.76.4`, tanpa AI agent/telemetry/proxy/remote font)                                                                 |
| FR-11 | Gerbang keamanan dokumentasi `DOCS_ENABLED`: default `true` di dev/test, default `false` (`404` problem) di produksi; produksi `DOCS_ENABLED=true` wajib HTTP Basic Auth constant-time dengan `DOCS_PASSWORD` >= 32 karakter (`401` bila salah, `500` bila misconfig) |
| FR-12 | Prisma generation/validation tanpa DB online; `getDb()` memvalidasi runtime URL dan lazy singleton per proses, tanpa koneksi saat import/build                                                                                                                        |
| FR-13 | Compose dev (PostgreSQL 5432, Chroma 8000, WAHA opt-in 3003) dan Compose VPS + Dockerfile non-root (`api`, `ai-service`, `worker`); hanya API publish ke loopback host VPS                                                                                            |
| FR-14 | CI push `dev`/PR target `dev` menjalankan quality, typecheck, unit/integration coverage (`>=80%` Node & Python), build, smoke 4 proses, dan validasi Compose tanpa DB/provider online                                                                                 |
| FR-15 | Dokumentasi Bahasa Indonesia mencakup root README, indeks, struktur, development, environment, architecture, deployment web/VPS, PRD v2.2, ADR 0001–0004, rencana implementasi, dan changelog                                                                         |

## 6. Toolchain dan command

- **Node.js & Frontend/API/Worker/DB**: Node **24.15.0**, npm **12.1.0**, Next.js **16.4.5**, React **19.3.1**, TypeScript **5.9.3**, Prisma **7.10.1**, ESLint **9.39.5**, Prettier **3.9.10**, Vitest **5.1.0**, Zod **4.6.7**, `@asteasolutions/zod-to-openapi` **9.1.0**, `@scalar/nextjs-api-reference` **0.12.15**.
- **Python AI Service**: Python **3.12** (`>=3.12,<3.14`), **uv 0.13.7**, FastAPI **0.162.0**, Pydantic **2.14.2**, Uvicorn **0.54.0**, `scalar-fastapi` **1.9.1**, `python-dotenv` **1.2.4**, Hatchling **1.33.0**; dev group: Pytest **9.2.0**, `pytest-cov` **7.1.0**, HTTPX2 **2.16.0**, Ruff **0.17.3**, Mypy **2.4.1**; optional extras (tidak dipasang default): `rag` (`langchain==1.4.8`, `chromadb==1.5.9`), `ml` (`scikit-learn==1.9.1`).
- **CDN Scalar**: `https://cdn.jsdelivr.net/npm/@scalar/api-reference@1.76.4` (dipin exact pada kedua backend; membutuhkan koneksi internet browser ke `cdn.jsdelivr.net` saat memuat UI `/docs`).

npm 12 memakai `allowScripts` root dengan persetujuan exact hanya untuk `prisma@7.10.1`, `@prisma/engines@7.10.1`, dan `esbuild@0.28.2`. Tidak ada blanket approval lifecycle scripts.

Kontrak root scripts lengkap di [development](development.md#semua-root-scripts-dan-script-workspace-ai): `build:packages`, `ai:sync`, `dev`, `dev:all`, `dev:web`, `dev:backend`, `dev:api`, `dev:worker`, `dev:ai`, `build`, `lint`, `typecheck`, `test`, `test:coverage`, `format`, `format:check`, `db:generate`, `db:validate`, `infra:up`, `infra:down`, `infra:config`, `infra:waha`, `start`, `start:all`, `start:backend`, `start:web`, `start:api`, `start:worker`, `start:ai`, `smoke`.

## 7. Persyaratan kualitas dan keamanan

- TypeScript strict, Mypy strict, dan arah dependency tidak membocorkan DB/secret ke browser; DB export browser dinonaktifkan dan lint menjaga boundary web.
- Error handler API dan AI service tidak boleh membocorkan pesan exception mentah, stack trace, payload input pengguna, query SQL, atau nilai environment pada respons maupun log error `500` yang tidak dikenal (log internal cukup mencatat tipe error, `requestId`, dan pathname).
- Gerbang dokumentasi produksi (`NODE_ENV=production` pada API, `APP_ENV=production` pada AI service) gagal tertutup (fail-closed):
  - `DOCS_ENABLED` default `false`; nilai selain `"true"`/`"false"` dianggap tidak valid dan menutup akses.
  - Saat nonaktif, `/docs` dan endpoint skema OpenAPI mengembalikan `404` Problem Details.
  - Saat diaktifkan di produksi (`DOCS_ENABLED=true`), `DOCS_USERNAME` wajib terisi dan `DOCS_PASSWORD` wajib minimal **32 karakter**; bila tidak memenuhi syarat, server mengembalikan `500` Problem Details generik dan tidak pernah melayani dokumen secara terbuka.
  - Verifikasi HTTP Basic Auth memakai perbandingan waktu konstan (constant-time) dengan dukungan UTF-8 yang konsisten; kegagalan autentikasi mengembalikan `401` Problem Details dengan header `WWW-Authenticate: Basic realm="Smart Catering Docs", charset="UTF-8"`.
  - Seluruh respons `/docs` dan skema OpenAPI menyertakan `Cache-Control: private, no-store` dan `Vary: Authorization`. Kredensial tidak pernah ditulis ke HTML, konfigurasi Scalar, query URL, atau log, dan tidak terkirim ke CDN jsDelivr. Pengaktifan di produksi wajib berada di balik reverse proxy TLS/HTTPS.
- Isolasi environment dua sumber: `apps/web` hanya membaca `apps/web/.env` (`NEXT_PUBLIC_APP_NAME` dan `API_BASE_URL` server-only) dan tidak membaca root `.env`. Launcher layanan dan loader Python menyaring root `.env` berdasarkan allowlist pemilik (tanpa interpolasi `${VAR}` atau mutasi global lintas proses, dengan variabel environment proses menang di atas file `.env`). Worker Fase 0 hanya menerima env listener (`NODE_ENV`, `WORKER_HOST`, `WORKER_PORT`), tanpa secret DB/WAHA/docs atau startup dependency pada PostgreSQL/Chroma/AI service.
- Minimum test coverage **80%** pada Vitest V8 (helper kontrak API, validasi environment worker, dan `scripts/service-environment.mjs`) serta **80%** pada Pytest `pytest-cov` (`apps/ai-service/app`).
- Smoke memakai built `web`, `api`, `worker`, dan `ai-service` dengan HTTP nyata untuk memverifikasi liveness, envelope REST, korelasi `X-Request-Id`, error RFC 9457, gerbang dokumentasi, serta shutdown bersih.

## 8. Acceptance dan bukti

| Area               | Bukti yang harus tersedia sebelum klaim lulus                                                                                                                     |
| ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Workspace/install  | Hasil `npm ci` root (enam workspace, satu `package-lock.json`) dan `npm run ai:sync` (`apps/ai-service/uv.lock` frozen tanpa extras)                              |
| Aplikasi & Kontrak | HTTP `web` (`:3000`), `api` (`:3001`), `worker` (`:3002`), `ai-service` (`:8001`) sesuai kontrak envelope, RFC 9457, `X-Request-Id`, paginasi, dan docs gate      |
| Kualitas           | Output aktual `format:check`, `lint`, `db:generate`, `db:validate`, `typecheck`, `test:coverage` (Node + Python >=80%), `build`, dan `smoke`                      |
| Server boundary    | Pembatasan import/export, redaksi error 500, fail-closed docs gate produksi, dan tidak ada credential/server code pada browser bundle                             |
| Infra              | Compose config valid; pada Docker engine nyata: image build/start (`api`, `ai-service`, `worker`), DB `SELECT 1`, Chroma health, isolasi port, volume persistence |
| CI                 | Definisi trigger/jobs Node + Python; run GitHub dan ruleset dilaporkan hanya jika benar-benar tersedia dan diamati                                                |
| Dokumentasi        | Nama env/script/port/kontrak selaras source, command lintas OS, tautan relevan, pemisahan bukti lama vs baru yang jujur                                           |
| Deployment         | Konfigurasi web-only Vercel dan VPS (`api`, `ai-service`, `worker`, infra) tersedia; deployment nyata bukan asumsi penerimaan file config                         |

Tabel ini adalah kriteria, **bukan checklist yang diklaim selesai oleh penulis dokumen**. Pelaksana integrasi memegang verifikasi terpadu setelah seluruh slice bergabung.

## 9. Dokumen turunan

[Arsitektur](architecture.md) · [ADR](decisions/README.md) · [Rencana pelaksanaan pengganti](superpowers/plans/2026-11-04-fase-0-setup-monorepo.md) · [Development](development.md) · [Environment](environment.md) · [Batas bukti](README.md#status-dan-batas-bukti)
