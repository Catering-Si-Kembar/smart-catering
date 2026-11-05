# Fase 0 — Rencana Implementasi Hybrid Minimal Monorepo (6-Workspace REST/OpenAPI & Python AI Foundation)

**Versi rencana:** 2.2 · **Diperbarui:** 2026-11-05 · **Status keputusan:** diterima

## Kedudukan dan audit awal

Dokumen ini **menggantikan seluruh rencana lama pada path yang sama**, bukan menambahkan arsitektur alternatif yang tetap berlaku. Acuan scope sekarang adalah [PRD Fase 0 v2.2](../../PRD_FASE_0.md) dan [ADR 0001–0004](../../decisions/README.md).

Audit awal repository menemukan hanya dokumen rencana ini; tidak ada source aplikasi, manifest/lockfile, atau monorepo pnpm untuk dimigrasikan. Implementasi Fase 0 membangun fondasi baru dengan npm Workspaces dan layanan Python `uv`.

## Tujuan

Membangun enam workspace yang dapat dipasang dari clean checkout (`npm ci` + `npm run ai:sync`), dijalankan lokal pada empat proses aplikasi (`web`, `api`, `ai-service`, `worker`), mematuhi standar kontrak wire REST (`data`/`meta`, RFC 9457 `application/problem+json`, `X-Request-Id`, validasi, paginasi) serta dokumentasi OpenAPI 3.1.0 + Scalar API Reference dengan gerbang keamanan produksi pada kedua backend (`api` dan `ai-service`), dan disiapkan untuk deployment hybrid: **web di Vercel; API, AI service, worker always-on serta PostgreSQL/Chroma/WAHA opt-in di VPS**. Tidak ada fitur bisnis, integrasi messaging nyata, pipeline RAG/ML aktif, training model, reminder/scheduler, atau resource cloud yang diaktifkan sebagai bagian scaffold.

## Keputusan tetap

| Area                 | Kontrak diterima                                                                                                                                                                                                                                                          |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Workspace (6 paket)  | `@smart-catering/web`, `api`, `ai-service`, `worker`, `db`, `types`; private, versi `0.0.0`, dependency internal Node exact `0.0.0`                                                                                                                                       |
| Package managers     | npm Workspaces (`apps/*`, `packages/*`) dengan satu root `package-lock.json`; Python `uv 0.13.7` dengan `apps/ai-service/uv.lock`                                                                                                                                         |
| Runtime Node/TS      | Node `24.15.0`, npm `12.1.0`, Next `16.4.5`, React `19.3.1`, TS `5.9.3`, Prisma `7.10.1`, ESLint `9.39.5`, Zod `4.6.7`, `@asteasolutions/zod-to-openapi@9.1.0`, `@scalar/nextjs-api-reference@0.12.15`                                                                    |
| Runtime Python AI    | Python `3.12` (`>=3.12,<3.14`), `uv 0.13.7`, `fastapi==0.162.0`, `pydantic==2.14.2`, `uvicorn==0.54.0`, `scalar-fastapi==1.9.1`, `python-dotenv==1.2.4`, `hatchling==1.33.0`; dev: `pytest==9.2.0`, `pytest-cov==7.1.0`, `httpx2==2.16.0`, `ruff==0.17.3`, `mypy==2.4.1`  |
| Optional Python deps | Extras `rag` (`langchain==1.4.8`, `chromadb==1.5.9`) dan `ml` (`scikit-learn==1.9.1`) dideklarasikan & dikunci, tidak dipasang default                                                                                                                                    |
| Install scripts      | `allowScripts` npm12 hanya `prisma@7.10.1`, `@prisma/engines@7.10.1`, `esbuild@0.28.2`; tidak ada blanket approval                                                                                                                                                        |
| Letak source         | `apps/web/app`, `apps/api/app` + `apps/api/lib`, dan `apps/ai-service/app` + `tests` tanpa `src`; `apps/worker/src` dan `packages/*/src` tetap `src`                                                                                                                      |
| Kepemilikan boundary | `apps/api` memiliki `modules/{auth,orders,inventory,finance}` & `integrations/waha` (`AI_SERVICE_URL`); `apps/ai-service` memiliki `app/{rag,ml,chroma}` (`CHROMA_URL`). Placeholder `rag`/`ml`/`chroma` di API dihapus                                                   |
| Sumber environment   | Hanya dua template/file aktif: root `.env.example` → `.env` (backend `api`/`ai-service`/`worker` via allowlist launcher, Prisma CLI, dan Compose) serta `apps/web/.env.example` → `apps/web/.env` (khusus frontend); tidak ada `.env` di workspace backend                |
| Kontrak REST         | Envelope `{ data, meta: { requestId, pagination? } }`, helper `204`, RFC 9457 `application/problem+json` (`400/401/403/404/405/422/500`), `X-Request-Id` UUID kanonis, paginasi safe integer `<= 9007199254740991`                                                        |
| OpenAPI & Scalar     | OpenAPI `3.1.0` mentah (`/api/openapi`, `/openapi.json`) & UI Scalar `/docs` dipin ke `https://cdn.jsdelivr.net/npm/@scalar/api-reference@1.76.4`; `DOCS_ENABLED` default `true` di dev/test, `false` di produksi, Basic Auth constant-time (`DOCS_PASSWORD` >= 32 chars) |
| Worker               | Proses Node mandiri di `:3002/health` dengan respons liveness internal `HealthData` `{"status":"ok","service":"worker"}` tanpa docs/secret                                                                                                                                |

## Irisan implementasi dan kepemilikan

### A. Kontrak REST Node (`apps/api` & `packages/types`)

- `packages/types`: mengekspor `HealthService` (`'api' | 'worker' | 'ai-service'`), `HealthData`, `ApiMeta`, `PaginationMeta`, `ApiSuccess<T>`, `HealthResponse`, `ValidationIssue`, dan `ProblemDetails`.
- `apps/api/lib/`: implementasi request context (`X-Request-Id`), response envelope (`200`/`201`/`204`), RFC 9457 Problem Details, validasi Zod (`400` malformed JSON vs `422 Unprocessable Content`), helper paginasi reusable, generator dokumen OpenAPI 3.1.0, serta gerbang keamanan `DOCS_ENABLED` / HTTP Basic Auth constant-time.
- `apps/api/app/`: route `/health`, `/docs`, `/api/openapi`, dan catch-all `404`/`405` (termasuk dukungan `HEAD` tanpa body). Menghapus boundary usang `modules/{rag,ml}` dan `integrations/chroma`.

### B. Layanan Python AI (`apps/ai-service`)

- `apps/ai-service/package.json`: wrapper task npm (`dev`, `start`, `build`, `lint`, `typecheck`, `test`, `test:coverage`, `format`, `format:check`) yang terintegrasi dengan launcher layanan dan `uv` tanpa dependency Node.
- `apps/ai-service/pyproject.toml`, `.python-version` (`3.12`), dan `app/`: implementasi FastAPI dengan kontrak wire yang identik dengan Node API (`/health`, `/docs`, `/openapi.json`, RFC 9457 handlers, `X-Request-Id`, validasi Pydantic dengan normalisasi path tanpa prefix `body`/`query`/`path`/`header`, helper paginasi, helper `204`, gerbang keamanan `DOCS_*`, dan pemuat `app/config.py` dari root `.env` dengan `interpolate=False` tanpa mutasi `os.environ`).
- `apps/ai-service/app/{rag,ml,chroma}/README.md`: dokumentasi batas modul RAG, ML, dan Chroma.
- `apps/ai-service/tests/`: pengujian ASGI Pytest menyeluruh dengan coverage minimal 80%.

### C. Infrastruktur Docker dan Dokumentasi (`infra/docker`, `docs`, `README.md`, `CHANGELOG.md`)

- `infra/docker/ai-service.Dockerfile`: image produksi non-root berbasis `python:3.12.16-slim-bookworm@sha256:e697c81897302a4c4333bade000d98038fbb21eb064f8ee1fd42d02ebcd9d337` dan `uv==0.13.7`, menjalankan `uv sync --frozen --no-dev` tanpa optional extras, melayani Uvicorn pada `0.0.0.0:8001`.
- `infra/docker/api.Dockerfile` dan `infra/docker/worker.Dockerfile`: menyalin keenam manifest `package.json` workspace pada tahap `deps` agar `npm ci` cocok dengan `package-lock.json` root tanpa membutuhkan Python di image Node.
- `infra/docker/compose.vps.yaml`: menambahkan service internal `ai-service` (tanpa publikasi port host, menerima `CHROMA_URL=http://chroma:8000` dan `DOCS_*`), memperbarui `api` (`AI_SERVICE_URL=http://ai-service:8001` dan `DOCS_*`), serta menjaga `worker` tetap bersih dari secret/kredensial.
- Pembaruan menyeluruh di tempat (in-place) untuk `README.md`, `CHANGELOG.md`, `docs/README.md`, `docs/PRD_FASE_0.md`, `docs/repository-structure.md`, `docs/development.md`, `docs/environment.md`, `docs/architecture.md`, `docs/deployment-vps.md`, `docs/deployment-vercel.md`, dan `docs/decisions/0001..0004`.

### D. Root Tooling, Lockfile, CI, dan Verifikasi Terpadu

- Root `package.json` (`dev`, `dev:all`, `dev:web`, `dev:backend`, `dev:api`, `dev:ai`, `dev:worker`, `start`, `start:all`, `start:backend`, `start:web`, `start:api`, `start:ai`, `start:worker`), `package-lock.json`, `turbo.json`, `vitest.config.ts`, `.env.example`, `apps/web/.env.example`, `.gitignore`, `.dockerignore`, `.prettierignore`, `.github/workflows/ci.yml`, `scripts/service-environment.mjs`, `scripts/run-service.mjs`, `scripts/smoke.mjs`, serta penyesuaian konsumen tipe di `apps/worker` dan `apps/web`.
- Resolusi `apps/ai-service/uv.lock` dan eksekusi seluruh rangkaian verifikasi terpadu.

## Urutan verifikasi clean checkout

```sh
npm ci
npm run ai:sync
npm run format:check
npm run lint
npm run db:generate
npm run db:validate
npm run typecheck
npm run test:coverage
npm run build
npm run smoke
```

## Status bukti

Hasil validasi lokal enam workspace beserta batas pengujiannya dicatat secara terpusat pada [indeks dokumentasi](../../README.md#status-dan-batas-bukti). Kelulusan lokal tidak membuktikan build image Docker, run CI GitHub, maupun deployment Vercel/VPS.
