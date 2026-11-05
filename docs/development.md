# Panduan pengembangan

**Diperbarui:** 2026-11-05

## 1. Prasyarat dan checkout

Gunakan Git, Node **24.15.0**, npm **12.1.0** (dipin melalui `.nvmrc` dan `packageManager`), serta Python **3.12** (`>=3.12,<3.14`, `.python-version` `3.12`) dan **uv 0.13.7**. Jalankan seluruh command dari root checkout sebenarnya.

```sh
node --version
npm --version
uv --version
npm ci
npm run ai:sync
```

- `npm ci` memakai satu `package-lock.json` root untuk seluruh enam workspace npm (`@smart-catering/web`, `api`, `ai-service`, `worker`, `db`, `types`). Untuk perubahan dependency Node gunakan `npm install` (atau `npm install <paket> --workspace=@smart-catering/api`) dan commit `package-lock.json`.
- `npm run ai:sync` menjalankan `uv sync --project apps/ai-service --frozen` menggunakan `apps/ai-service/uv.lock`. Bila Python 3.12 belum terpasang secara global di mesin pengembang, `uv` dapat menyediakan runtime Python 3.12 terkelola (misalnya `3.12.13`) tanpa mengubah instalasi Python sistem lain.
- **Kebijakan Optional Extras Python (`rag` dan `ml`)**: `apps/ai-service/pyproject.toml` mendeklarasikan optional extras `rag` (`langchain==1.4.8`, `chromadb==1.5.9`) dan `ml` (`scikit-learn==1.9.1`). Sinkronisasi default (`npm run ai:sync`) maupun build container produksi (`uv sync --frozen --no-dev`) **tidak** memasang extras tersebut dan tidak menjalankan training atau pemuatan model. Jika pada fase mendatang pengembangan RAG/ML diaktifkan, gunakan `uv sync --project apps/ai-service --frozen --extra rag` atau `--extra ml`.
- npm 12 menerapkan `allowScripts` dari manifest root. Persetujuan terbatas pada `prisma@7.10.1`, `@prisma/engines@7.10.1`, dan `esbuild@0.28.2`; tidak ada persetujuan semua dependency. ESLint tetap **9.39.5** agar sesuai plugin Next pada fondasi ini.

Docker Engine/Desktop dan Compose v2 diperlukan hanya untuk jalur infrastruktur (`postgres`, `chroma`, `waha`) dan build container VPS.

## 2. Environment

Salin kedua template `.env.example` (`.env` di root dan `apps/web/.env`) sesuai [README](../README.md#quick-start), lalu tinjau [environment](environment.md):

- Frontend `apps/web` hanya membaca `apps/web/.env` melalui loader native Next.js (`NEXT_PUBLIC_APP_NAME` dan `API_BASE_URL` server-only) dan tidak membaca root `.env`.
- Layanan backend native (`api`, `ai-service`, `worker`) dijalankan melalui launcher bersama `scripts/run-service.mjs` (`scripts/service-environment.mjs`) yang mem-parse root `.env` (`util.parseEnv` tanpa ekspansi `${VAR}`) dan menyaring variabel sesuai allowlist masing-masing layanan.
- Loader Python (`apps/ai-service/app/config.py`) juga membaca root `.env` secara langsung dan terisolasi (`interpolate=False`, hanya key milik `AppSettings`, tanpa memutasi `os.environ` global dan tanpa fallback ke `apps/ai-service/.env`).
- Prisma CLI (`packages/db/prisma.config.ts`) membaca `DATABASE_URL` dari root `.env` tanpa mutasi global (dengan fallback sintaktis khusus `generate` dan `validate` bila `DATABASE_URL` kosong).
- Docker Compose membaca root `.env` melalui `--env-file .env`.
- Tidak ada file `.env` atau `.env.example` tambahan di dalam `apps/api`, `apps/ai-service`, `apps/worker`, maupun `packages/db`. Variabel yang diinjeksikan langsung pada proses selalu menang di atas nilai file `.env`.

Jalur offline landing, health API/AI/worker, dan dokumentasi OpenAPI/Scalar (`/docs`, `/api/openapi`, `/openapi.json`) tidak memerlukan key WAHA, Chroma, atau DB hidup.

## 3. Menjalankan aplikasi tanpa infra

```sh
npm run db:generate
npm run dev
```

Root `dev` membangun `db` dan `types` terlebih dahulu, lalu menjalankan **web (`:3000`) dan API (`:3001`)**. Pilihan command development lainnya dari root repository:

```sh
# Semua aplikasi (web + api + worker + ai-service)
npm run dev:all

# Hanya frontend (web)
npm run dev:web

# Semua layanan backend (api + ai-service + worker)
npm run dev:backend

# Layanan backend individual
npm run dev:api
npm run dev:ai
npm run dev:worker
```

Launcher `dev*` menetapkan mode `development` secara otomatis (`NODE_ENV=development` untuk Node dan `APP_ENV=development` untuk AI service) serta memakai host/port dari root `.env` (`API_HOST`/`API_PORT` default `127.0.0.1:3001`, `AI_HOST`/`AI_PORT` default `127.0.0.1:8001`, `WORKER_HOST`/`WORKER_PORT` default `127.0.0.1:3002`). Setiap proses foreground dihentikan dengan **Ctrl+C**.

| Proses     | Endpoint lokal yang dapat diperiksa                                                                                                        |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| Web        | `http://localhost:3000` (landing setup Smart Catering)                                                                                     |
| API        | `http://localhost:3001/health` (`{"data":{"status":"ok","service":"api"},"meta":{"requestId":"<uuid>"}}`), `/docs`, `/api/openapi`         |
| AI Service | `http://127.0.0.1:8001/health` (`{"data":{"status":"ok","service":"ai-service"},"meta":{"requestId":"<uuid>"}}`), `/docs`, `/openapi.json` |
| Worker     | `http://127.0.0.1:3002/health` (liveness internal `{"status":"ok","service":"worker"}`; path lain 404, method selain GET 405)              |

Catatan UI Scalar (`/docs`): halaman `/docs` pada API (`:3001/docs`) dan AI service (`:8001/docs`) aktif secara default saat `NODE_ENV`/`APP_ENV` bukan `production` (`DOCS_ENABLED=true`). Browser memerlukan koneksi internet untuk memuat bundle klasik yang dipin dari `https://cdn.jsdelivr.net/npm/@scalar/api-reference@1.76.4`, sedangkan endpoint skema `/api/openapi` dan `/openapi.json` disajikan sepenuhnya secara lokal.

## 4. Infrastruktur lokal — jalur ber-Docker

Isi root `.env` dengan **`POSTGRES_PASSWORD` dan `WAHA_API_KEY`** acak yang kuat dan berbeda sebelum command Compose apa pun. Interpolasi required variables terjadi sebelum profile disaring; key tetap diperlukan meski service WAHA belum dijalankan.

```sh
docker --version
docker compose version
npm run infra:config
npm run infra:up
docker compose --env-file .env -f infra/docker/compose.dev.yaml ps
docker compose --env-file .env -f infra/docker/compose.dev.yaml exec postgres sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
docker compose --env-file .env -f infra/docker/compose.dev.yaml exec postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT 1;"'
```

Default Compose dev hanya menjalankan PostgreSQL di loopback `5432` dan Chroma di loopback `8000` (layanan `ai-service` dijalankan di host melalui `npm run dev:ai` atau `npm run dev:all` saat pengembangan lokal). Untuk menjalankan service WAHA secara opsional pada loopback `3003`:

```sh
npm run infra:waha
```

Shutdown biasa tanpa menghapus named volumes:

```sh
npm run infra:down
```

## 5. Build dan production lokal

```sh
npm run db:generate
npm run db:validate
npm run build
```

`npm run build` menjalankan task `build` di seluruh enam workspace melalui Turbo (`packages/types`, `packages/db`, `apps/web`, `apps/api`, `apps/worker`, serta `uv build` pada `apps/ai-service`).

Untuk menjalankan hasil build di mesin lokal:

- `npm run start`: menjalankan built **web + API** (default).
- `npm run start:all`: menjalankan keempat aplikasi hasil build (**web + API + worker + ai-service**).
- `npm run start:backend`: menjalankan ketiga layanan backend hasil build (**API + ai-service + worker**).
- `npm run start:web` / `npm run start:api` / `npm run start:ai` / `npm run start:worker`: menjalankan masing-masing proses hasil build secara terpisah.

Launcher `start*` menetapkan mode produksi tanpa syarat (`NODE_ENV=production` pada Node dan `APP_ENV=production` pada AI service). Built API dijalankan melalui standalone server (`apps/api/.next/standalone/apps/api/server.js`) dengan memetakan `API_HOST` → `HOSTNAME` dan `API_PORT` → `PORT` tanpa memercayai `HOSTNAME`/`PORT` warisan shell. `start:ai` menjalankan Uvicorn tanpa reload dan dengan `--no-access-log` pada `AI_HOST`:`AI_PORT`.

## Pemeriksaan sebelum PR

Pelaksana integrasi menjalankan pemeriksaan terpadu setelah seluruh perubahan masuk. Urutan acuan dari clean checkout:

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

- `npm run format:check`: memeriksa format kode dengan Prettier pada seluruh repo dan `ruff format --check app tests` pada `apps/ai-service`.
- `npm run lint`: menjalankan ESLint pada workspace Node/TS dan `ruff check .` pada `apps/ai-service` melalui Turbo.
- `npm run typecheck`: menjalankan `tsc --noEmit` pada workspace TypeScript dan `mypy app` (strict) pada `apps/ai-service` melalui Turbo.
- `npm run test:coverage`: menjalankan Vitest dengan V8 coverage (threshold minimal 80% pada helper API, environment worker, dan `scripts/service-environment.mjs`) diikuti Pytest dengan `pytest-cov` (`--cov=app --cov-fail-under=80`) pada `apps/ai-service`.
- `npm run smoke`: menjalankan built `web` (`:3000`), `api` (`:3001`), `worker` (`:3002`), dan `ai-service` (`:8001`), memverifikasi kontrak liveness, envelope `{ data, meta }`, korelasi `X-Request-Id`, error RFC 9457 (`404`/`405`), OpenAPI 3.1.0 & Scalar `/docs`, serta shutdown bersih keempat proses. Bebaskan port `3000`, `3001`, `3002`, dan `8001` sebelum menjalankan smoke.

## Semua root scripts dan script workspace AI

### Root scripts (`package.json`)

| Script                                                    | Fungsi                                                                                                                    |
| --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `ai:sync`                                                 | `uv sync --project apps/ai-service --frozen` (tanpa optional extras)                                                      |
| `build:packages`                                          | Build shared `db` dan `types`                                                                                             |
| `dev` / `dev:all`                                         | Shared build lalu `web` + `api` (default) / keempat aplikasi (`web`, `api`, `worker`, `ai-service`)                       |
| `dev:web` / `dev:backend`                                 | Build `types` lalu frontend `web` saja / build `db` + `types` lalu ketiga layanan backend (`api`, `ai-service`, `worker`) |
| `dev:api` / `dev:ai` / `dev:worker`                       | Prebuild paket yang dibutuhkan (`db` + `types` untuk `api`, `types` untuk `worker`) lalu jalankan layanan terpilih        |
| `build` / `lint` / `typecheck`                            | Task Turbo seluruh enam workspace (Node/TS + Python Ruff/Mypy/Hatchling)                                                  |
| `test` / `test:coverage`                                  | Vitest run + Pytest / Vitest V8 coverage (`>=80%`) + Pytest coverage (`>=80%`)                                            |
| `format` / `format:check`                                 | Prettier + Ruff format write / check                                                                                      |
| `db:generate` / `db:validate`                             | Prisma generate / validasi schema tanpa migrasi (membaca `DATABASE_URL` dari root `.env` bila tersedia)                   |
| `infra:up` / `infra:down` / `infra:config` / `infra:waha` | Operasi Docker Compose dev (`postgres`, `chroma`, dan profile opsional `waha`)                                            |
| `start` / `start:all`                                     | Menjalankan built `web` + `api` (default) / keempat aplikasi hasil build                                                  |
| `start:backend`                                           | Menjalankan ketiga layanan backend hasil build (`api`, `ai-service`, `worker`)                                            |
| `start:web` / `start:api` / `start:ai` / `start:worker`   | Menjalankan masing-masing aplikasi hasil build secara terpisah                                                            |
| `smoke`                                                   | Built HTTP, kontrak REST/OpenAPI, dan lifecycle checks pada keempat proses aplikasi tanpa infra                           |

### Script workspace `@smart-catering/ai-service` (`apps/ai-service/package.json`)

| Script workspace | Perintah launcher / `uv`                                                                                                                        |
| ---------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `dev`            | `node ../../scripts/run-service.mjs ai dev` → `uv run --frozen uvicorn app.main:app --host <AI_HOST> --port <AI_PORT> --reload --no-access-log` |
| `start`          | `node ../../scripts/run-service.mjs ai start` → `uv run --frozen uvicorn app.main:app --host <AI_HOST> --port <AI_PORT> --no-access-log`        |
| `build`          | `node ../../scripts/run-service.mjs ai build` → `uv build`                                                                                      |
| `lint`           | `uv run --frozen ruff check .`                                                                                                                  |
| `typecheck`      | `uv run --frozen mypy app`                                                                                                                      |
| `test`           | `uv run --frozen pytest`                                                                                                                        |
| `test:coverage`  | `uv run --frozen pytest --cov=app --cov-report=term-missing --cov-report=xml --cov-fail-under=80`                                               |
| `format`         | `uv run --frozen ruff format app tests`                                                                                                         |
| `format:check`   | `uv run --frozen ruff format --check app tests`                                                                                                 |

## Troubleshooting

| Gejala                                            | Tindakan                                                                                                                      |
| ------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| Node/npm atau `uv`/Python berbeda                 | Cocokkan Node `24.15.0`, npm `12.1.0`, `uv 0.13.7`, dan Python `3.12`; jalankan `npm run ai:sync` setelah `npm ci`            |
| `uv run --frozen` gagal karena `.venv` belum siap | Jalankan `npm run ai:sync` dari root repository; jangan menghapus `apps/ai-service/uv.lock`                                   |
| `/docs` atau `/api/openapi` / `/openapi.json` 404 | Periksa `DOCS_ENABLED`: pada `NODE_ENV=production` atau `APP_ENV=production`, nilai default adalah `false`                    |
| `/docs` mengembalikan 500 di mode produksi        | Saat `DOCS_ENABLED=true` di produksi, `DOCS_USERNAME` wajib diisi dan `DOCS_PASSWORD` wajib minimal 32 karakter (fail-closed) |
| UI `/docs` kosong saat offline penuh              | Bundle Scalar dipin ke `https://cdn.jsdelivr.net/npm/@scalar/api-reference@1.76.4`; browser butuh akses ke `cdn.jsdelivr.net` |
| Port sibuk saat `dev:all` atau `smoke`            | Pastikan port `3000` (web), `3001` (api), `3002` (worker), dan `8001` (ai-service) tidak sedang dipakai proses lain           |
| Infra interpolation menolak secret kosong         | Isi kedua `POSTGRES_PASSWORD` dan `WAHA_API_KEY` di root `.env` sebelum command Compose apa pun                               |

Lihat [batas bukti](README.md#status-dan-batas-bukti), [environment](environment.md), dan [deployment VPS](deployment-vps.md) sebelum menyimpulkan siap produksi.
