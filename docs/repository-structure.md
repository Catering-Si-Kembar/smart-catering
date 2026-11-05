# Struktur repository dan ownership source

**Diperbarui:** 2026-11-05

Repository memakai tepat **enam npm workspace private** dengan versi `0.0.0`. `apps/*` dan `packages/*` pada manifest root adalah satu-satunya definisi workspace npm, sementara `apps/ai-service` menggabungkan wrapper `package.json` tipis (tanpa dependency Node) dengan proyek Python `uv` (`pyproject.toml` + `uv.lock`). Tree berikut memetakan source fondasi; output generated dipisahkan di bagian akhir, bukan dianggap source yang perlu di-commit.

## Peta utama

```text
apps/
  web/
    package.json, tsconfig.json, next.config.ts, eslint.config.mjs
    .env.example
    app/{layout.tsx,page.tsx,globals.css}
  api/
    package.json, tsconfig.json, next.config.ts, eslint.config.mjs
    app/
      health/route.ts
      docs/route.ts
      api/openapi/route.ts
      [...catchall]/route.ts
    lib/                       # Helper kontrak REST, OpenAPI 3.1, error RFC 9457, requestId, validasi, paginasi, docs gate (+ unit tests)
    modules/{auth,orders,inventory,finance}/
    integrations/waha/
  ai-service/
    package.json               # Task wrapper npm/Turbo saja (tanpa dependency Node)
    pyproject.toml, uv.lock, .python-version
    app/
      __init__.py, main.py, config.py, schemas.py, errors.py, pagination.py, docs.py, openapi.py
      rag/README.md
      ml/README.md
      chroma/README.md
    tests/                     # Pytest ASGI tests untuk health, error RFC 9457, requestId, paginasi, 204, docs security
  worker/
    package.json, tsconfig.json
    src/{index.ts,environment.ts,environment.test.ts}
    src/jobs/                  # Reservasi lokal; belum ada file yang di-track
    src/schedulers/            # Reservasi lokal; belum ada file yang di-track
packages/
  db/
    package.json, tsconfig.json, prisma.config.ts
    prisma/schema.prisma
    src/{index.ts,client.ts}
  types/
    package.json, tsconfig.json
    src/index.ts
infra/docker/
  api.Dockerfile
  ai-service.Dockerfile
  worker.Dockerfile
  compose.dev.yaml
  compose.vps.yaml
scripts/
  run-service.mjs, service-environment.mjs, smoke.mjs
.github/workflows/ci.yml
docs/
  README.md, PRD_FASE_0.md, repository-structure.md, development.md
  architecture.md, environment.md, deployment-vercel.md, deployment-vps.md
  decisions/
  superpowers/plans/2026-11-04-fase-0-setup-monorepo.md
README.md, CHANGELOG.md
package.json, package-lock.json, turbo.json
tsconfig.base.json, eslint.config.mjs, vitest.config.ts
.prettierrc.json, .prettierignore, .nvmrc, .gitignore, .dockerignore, .env.example
```

Tree disingkat untuk navigasi, bukan daftar setiap file atau hasil audit build. Tidak memakai `.gitkeep`. Direktori modul bisnis API (`auth`, `orders`, `inventory`, `finance`), integrasi API (`waha`), serta boundary AI service (`rag`, `ml`, `chroma`) tetap tersimpan karena memiliki `README.md` yang menjelaskan batas kepemilikan. Direktori `jobs` dan `schedulers` pada worker yang masih kosong hanyalah target lokal fase mendatang dan tidak ikut Git pada clone baru sampai memiliki source nyata.

Konvensi direktori source:

- **Next.js apps (`apps/web`, `apps/api`)**: langsung memakai `app/` di root workspace tanpa lapisan `src`. Helper kontrak REST dan OpenAPI API berada di `apps/api/lib/`.
- **Python AI service (`apps/ai-service`)**: langsung memakai paket flat `app/` dan `tests/` di root workspace tanpa lapisan `src`.
- **Node worker dan shared packages (`apps/worker`, `packages/db`, `packages/types`)**: tetap memakai `src/` yang dikompilasi ke `dist/`.

## Workspace dan kontrak

| Workspace                    | Entry/export utama                                                                                     | Pemakai dan dependency                                             | Status Fase 0                                                 |
| ---------------------------- | ------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------ | ------------------------------------------------------------- |
| `@smart-catering/web`        | `app/page.tsx`, `layout.tsx`, `globals.css`                                                            | Next/React, shared types; dilarang DB/API/worker/AI server imports | Landing setup di `:3000`, Vercel saja                         |
| `@smart-catering/api`        | `app/health/route.ts`, `app/docs/route.ts`, `app/api/openapi/route.ts`, `lib/*`                        | Next/React, Zod/OpenAPI/Scalar, `db`, `types`; modul bisnis & WAHA | REST backend di `:3001`; standalone VPS                       |
| `@smart-catering/ai-service` | `app/main.py` (`app.main:app` → `/health`, `/docs`, `/openapi.json`)                                   | Python 3.12, `uv`, FastAPI, Pydantic, Uvicorn, `scalar-fastapi`    | REST AI backend di `:8001`; internal VPS; owner RAG/ML/Chroma |
| `@smart-catering/worker`     | `src/index.ts` → built `dist/index.js`                                                                 | Node, `types`; tidak import `apps/api` atau `apps/ai-service`      | Liveness internal di `:3002`, shutdown; tidak ada job         |
| `@smart-catering/db`         | `src/index.ts` → `getDb`, `resolveDatabaseUrl`, `PrismaClient`                                         | Prisma/adapter-pg/pg; API dan kelak worker server                  | Lazy client, schema tanpa model bisnis; browser export `null` |
| `@smart-catering/types`      | `src/index.ts` → `HealthData`, `ApiSuccess`, `HealthResponse`, `ProblemDetails`, `PaginationMeta`, dll | Shared TypeScript contract tanpa provider/secret                   | Kontrak wire REST & health untuk TypeScript workspaces        |

`db` dan `types` mengekspor `dist/index.js` serta deklarasi type `dist/index.d.ts`, bukan source TS langsung. Build packages memakai ESM NodeNext; dependency internal Node exact `0.0.0` ditaut npm. Jangan membuat shim/re-export lintas app untuk melewati ownership.

### Pemisahan modul bisnis API vs boundary AI Service

- **Milik `apps/api`**:
  - `apps/api/modules/{auth,orders,inventory,finance}`: tempat perilaku domain bisnis transaksional pada fase mendatang (saat ini hanya README batas modul).
  - `apps/api/integrations/waha`: boundary adapter WhatsApp HTTP API (tanpa HTTP call/session aktif pada Fase 0).
  - `apps/api/lib`: implementasi nyata Fase 0 untuk request context (`X-Request-Id`), response envelope (`200`/`201`/`204`), RFC 9457 Problem Details, validasi Zod, paginasi, registrasi skema OpenAPI 3.1.0, dan gerbang autentikasi dokumentasi (`DOCS_*`).
- **Milik `apps/ai-service`**:
  - `apps/ai-service/app/{rag,ml,chroma}`: boundary resmi untuk pipeline Retrieval-Augmented Generation, model Machine Learning, dan koneksi vector store Chroma pada fase mendatang (saat ini hanya README batas modul; optional extras `rag` dan `ml` dideklarasikan di `pyproject.toml` tanpa di-install secara default).
  - Direktori lama `apps/api/modules/rag`, `apps/api/modules/ml`, dan `apps/api/integrations/chroma` **telah dihapus** dari `apps/api`.

Tidak ada packages UI/config/utils/services/RAG/ML terpisah, Telegram, Redis, atau BullMQ.

## Tanggung jawab file root

| File                                                 | Tanggung jawab                                                                                                                                                 |
| ---------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `package.json`                                       | Workspace graph enam paket, versi runtime/package manager, root scripts Node + Python (`dev:all`, `dev:backend`, `start:all`, `start:backend`, `ai:sync`, dll) |
| `package-lock.json`                                  | Satu sumber resolusi dependency npm untuk `npm ci` seluruh workspace Node (termasuk wrapper `apps/ai-service`)                                                 |
| `turbo.json`                                         | Urutan dependency `^build`, output cache, forwarding env (`UV_*`, `NODE_ENV`, `API_HOST`, `API_PORT`, `AI_HOST`, `AI_PORT`, `DOCS_*`, `AI_SERVICE_URL`, dll)   |
| `tsconfig.base.json`                                 | Strict TS, target ES2022, konfigurasi dasar; workspace Node menimpa module/resolution NodeNext                                                                 |
| `eslint.config.mjs`                                  | Flat config bersama dan boundary import frontend/server                                                                                                        |
| `vitest.config.ts`                                   | Unit test & V8 coverage untuk `apps/api/lib`, `apps/worker/src`, dan `scripts/` (threshold minimum 80%)                                                        |
| `.prettierrc.json`, `.prettierignore`                | Format source/docs dan pengecualian generated/Python venv                                                                                                      |
| `.nvmrc`                                             | Pin Node lokal/CI (`24.15.0`)                                                                                                                                  |
| `.gitignore`, `.dockerignore`                        | Pisahkan source dari secret, output build, `.venv`, cache pytest/mypy/ruff, dan context lokal                                                                  |
| `.env.example`                                       | Template env root terpusat untuk backend (`api`, `ai-service`, `worker` via allowlist), Prisma CLI, dan Compose (`apps/web` memiliki `apps/web/.env.example`)  |
| `.github/workflows/ci.yml`                           | Push dev/PR target dev: quality, unit coverage Node + Python, smoke 4 proses, model Compose dan build image VPS                                                |
| `scripts/run-service.mjs`, `service-environment.mjs` | Launcher layanan (`web`, `api`, `ai`, `worker`) dan pemuat allowlist root `.env` tanpa membocorkan secret antar-layanan                                        |
| `scripts/smoke.mjs`                                  | Built web/API/worker/ai-service HTTP, kontrak REST/error/requestId/docs, dan lifecycle checks tanpa readiness infra                                            |

## Source, generated, dan data lokal

| Artefak                                                                                    | Perlakuan                                                                                            |
| ------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------- |
| `node_modules/`, `.turbo/`                                                                 | Hasil install/cache Node; jangan commit                                                              |
| `apps/ai-service/.venv/`, `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/` | Environment dan cache Python lokal; jangan commit atau salin ke image Docker                         |
| `apps/ai-service/dist/`                                                                    | Output wheel/sdist dari `uv build`; jangan commit                                                    |
| `.next/`, termasuk `.next/standalone/`                                                     | Build Next; generate dari source/lockfile                                                            |
| `next-env.d.ts` pada tiap Next app                                                         | Deklarasi generated oleh Next; diabaikan Git/formatter dan tidak diedit manual                       |
| `packages/*/dist/`, `apps/worker/dist/`                                                    | Hasil TypeScript; bukan source untuk diedit                                                          |
| `packages/db/src/generated/prisma/`                                                        | Hasil `db:generate`; tidak di-commit/diedit manual                                                   |
| `coverage/`, `apps/ai-service/coverage.xml`, `.coverage`                                   | Report coverage dari run aktual, bukan coverage badge otomatis                                       |
| `.env`, `apps/web/.env`                                                                    | Dua file environment lokal aktif (root backend/Compose + frontend); jangan commit atau copy ke image |
| `.env.example`, `apps/web/.env.example`, `apps/ai-service/uv.lock`                         | Dua source template env resmi dan lockfile Python yang wajib di-track                                |
| Named volumes Docker                                                                       | Data persistent runtime, di luar source Git; backup terpisah                                         |

## Di mana menambahkan perubahan?

- Halaman/komponen khusus frontend → `apps/web/app` atau folder lokal web yang sesuai.
- Route HTTP API utama → `apps/api/app`, helper kontrak HTTP/OpenAPI API → `apps/api/lib`, perilaku domain bisnis → `apps/api/modules/{auth,orders,inventory,finance}`, adapter WAHA → `apps/api/integrations/waha`.
- Endpoint dan kontrak HTTP AI service → `apps/ai-service/app`, fitur RAG/ML/Chroma mendatang → `apps/ai-service/app/{rag,ml,chroma}`, pengujian Python → `apps/ai-service/tests`.
- Schema dan DB client → `packages/db/src` (schema tetap `packages/db/prisma`); shared TypeScript contract lintas proses → `packages/types/src`.
- Job background masa depan → `apps/worker/src/jobs`, dengan worker tetap independen dari `apps/api` dan `apps/ai-service`.

Lihat [arsitektur](architecture.md) untuk arah dependency dan [development](development.md) untuk urutan build. Peta ini tidak menyatakan hasil checks atau deployment; [batas bukti](README.md#status-dan-batas-bukti) tetap berlaku.
