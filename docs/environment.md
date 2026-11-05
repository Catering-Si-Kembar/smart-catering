# Environment dan pengelolaan rahasia

**Diperbarui:** 2026-11-05

## Dua sumber file environment dan mekanisme pemuatan

Repository ini hanya menggunakan **dua file `.env` aktif** yang disalin dari dua template `.env.example`:

| Template → file lokal                     | Pemilik / pemuat                                                                                                           | Cakupan dan batas isolasi                                                                                                        |
| ----------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `.env.example` → `.env` (root)            | Launcher layanan (`scripts/service-environment.mjs`), loader Python (`apps/ai-service/app/config.py`), Prisma CLI, Compose | Sumber terpusat backend (`api`, `ai-service`, `worker`), Prisma tooling, dan interpolasi Compose; difilter per allowlist layanan |
| `apps/web/.env.example` → `apps/web/.env` | Loader native Next.js pada workspace `@smart-catering/web`                                                                 | Khusus frontend (`NEXT_PUBLIC_APP_NAME` dan `API_BASE_URL` server-only); tidak pernah membaca root `.env`                        |

### Mengapa tidak ada `.env` / `.env.example` di workspace backend?

Workspace `apps/api`, `apps/ai-service`, `apps/worker`, `packages/db`, dan `packages/types` **tidak memiliki file `.env` maupun `.env.example` tersendiri** (dan tidak ada fallback ke file `.env` per-workspace lama):

- **Menghilangkan duplikasi 6 file:** seluruh konfigurasi native backend, listener port, Prisma CLI, dan Docker Compose dikelola dari satu root `.env`, sedangkan konfigurasi frontend tetap terpisah di `apps/web/.env`.
- **Isolasi berbasis allowlist (bukan export global):** launcher `scripts/run-service.mjs` membaca root `.env` menggunakan `util.parseEnv` bawaan Node.js dan hanya meneruskan variabel yang diizinkan untuk layanan terkait (ditambah variabel OS/tooling esensial). Root `.env` **tidak** di-export secara mentah ke seluruh proses workspace.
- **Container hanya menerima environment eksplisit:** image Docker VPS tidak menyalin file `.env` dari host. Container `api`, `ai-service`, dan `worker` hanya menerima variabel yang dideklarasikan secara eksplisit pada blok `environment` di `infra/docker/compose.vps.yaml`. Pada Vercel, environment disetel di pengaturan project web (`NEXT_PUBLIC_APP_NAME` dan `API_BASE_URL`), bukan dengan mengunggah root `.env`.

Salin kedua template sekali menggunakan perintah PowerShell atau macOS/Linux di [quick start](../README.md#quick-start). Jangan menimpa file lokal yang sudah berisi rahasia.

Setelah mengubah root `.env`, hentikan lalu jalankan kembali service yang terdampak; launcher membaca konfigurasi saat proses dimulai. Jika mengubah `API_PORT`, sesuaikan `API_BASE_URL` di `apps/web/.env`. Jika mengubah `AI_PORT`, sesuaikan `AI_SERVICE_URL` di root `.env` sebelum integrasi antar-service dipakai.

## Aturan presedensi, parsing, dan mode runtime

1. **Presedensi variabel (`process.env` / `os.environ` > root `.env` > default aplikasi):**
   - Variabel konfigurasi milik service yang diinjeksikan langsung pada proses/shell menang di atas nilai root `.env`; mode lifecycle `NODE_ENV`/`APP_ENV` mengikuti command launcher sebagaimana dijelaskan di bawah.
   - Ketiadaan file root `.env` diizinkan untuk pengujian liveness/default offline maupun eksekusi di dalam container; error pembacaan filesystem selain `ENOENT` tetap dilemparkan (fail-fast).
2. **Parsing tanpa interpolasi `${VAR}` pada runtime aplikasi:**
   - Baik Node.js (`util.parseEnv` di `scripts/service-environment.mjs` dan `packages/db/prisma.config.ts`) maupun Python (`dotenv_values(..., interpolate=False)` di `apps/ai-service/app/config.py`) mem-parse isi `.env` secara literal **tanpa** ekspansi `${VAR}` dan **tanpa** memutasi `os.environ` global lintas proses.
   - Sebaliknya, **Docker Compose** (`docker compose --env-file .env`) melakukan interpolasi `${VAR}` saat mengevaluasi `infra/docker/compose.dev.yaml` dan `infra/docker/compose.vps.yaml`.
3. **Pengendalian mode (`NODE_ENV` dan `APP_ENV`) oleh launcher:**
   - Baik `NODE_ENV` maupun `APP_ENV` tidak ditulis di dalam root `.env.example`. Demi keamanan mode runtime, launcher npm menetapkan `NODE_ENV=development` (Node) dan `APP_ENV=development` (`ai-service`) tanpa syarat pada command `dev*`, serta menetapkan `NODE_ENV=production` pada `build`/`start*` dan `APP_ENV=production` pada `start*`.
4. **Perilaku default `DOCS_ENABLED` yang dikosongkan pada template:**
   - Pada root `.env.example`, `DOCS_ENABLED=` sengaja dikosongkan. Saat kosong atau tidak disetel, aplikasi mengaktifkan dokumentasi (`true`) pada mode `development`/`test` dan menonaktifkannya (`false`) pada mode `production`.
   - Pada `infra/docker/compose.vps.yaml`, ekspresi `${DOCS_ENABLED:-false}` memastikan dokumentasi container VPS tetap nonaktif secara default bila `DOCS_ENABLED` di root `.env` kosong.

## Kepemilikan variabel aplikasi dan Prisma tooling

| Variabel               | Sumber file              | Pemilik allowlist   | Browser/server                | Kapan dibutuhkan & perilaku default                                                                                                                                          |
| ---------------------- | ------------------------ | ------------------- | ----------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `NEXT_PUBLIC_APP_NAME` | `apps/web/.env`          | `web`               | Publik                        | Branding halaman frontend; default `Smart Catering`                                                                                                                          |
| `API_BASE_URL`         | `apps/web/.env`          | `web`               | Server-only                   | Future SSR/server action ke API (belum dipakai landing Fase 0); default `http://localhost:3001`                                                                              |
| `API_HOST`             | Root `.env`              | `api`               | Server-only                   | Host listener native `dev:api`/`start:api`; default `127.0.0.1` (mengabaikan `HOSTNAME` liar shell)                                                                          |
| `API_PORT`             | Root `.env`              | `api`, Compose VPS  | Server-only                   | Port listener native API (`3001`) sekaligus mapping loopback host VPS `127.0.0.1:${API_PORT:-3001}:3001`                                                                     |
| `DATABASE_URL`         | Root `.env`              | `api`, `db` tooling | Server-only, rahasia          | Kosong di template; dipakai saat `getDb()` dipanggil atau Prisma CLI dijalankan                                                                                              |
| `AI_SERVICE_URL`       | Root `.env`              | `api`               | Server-only                   | Alamat internal layanan AI masa depan; default `http://127.0.0.1:8001` (lokal) / `http://ai-service:8001` (VPS)                                                              |
| `WAHA_BASE_URL`        | Root `.env`              | `api`               | Server-only                   | Integrasi WAHA masa depan; default `http://127.0.0.1:3003` (lokal) / `http://waha:3000` (VPS)                                                                                |
| `WAHA_API_KEY`         | Root `.env`              | `api`, Compose      | Server-only, rahasia          | Kosong di template; wajib diisi sebelum command Compose apa pun                                                                                                              |
| `AI_HOST`              | Root `.env`              | `ai-service` (CLI)  | Server-only                   | Host Uvicorn pada command native (`dev:ai`/`start:ai`); default `127.0.0.1` (container tetap `0.0.0.0`)                                                                      |
| `AI_PORT`              | Root `.env`              | `ai-service` (CLI)  | Server-only                   | Port Uvicorn pada command native (`dev:ai`/`start:ai`); default `8001` (container tetap `8001`)                                                                              |
| `APP_ENV`              | Launcher / container env | `ai-service`        | Server-only                   | Mode runtime FastAPI (`development`, `test`, `production`); ditetapkan tanpa syarat oleh launcher (`dev` → `development`, `start` → `production`) atau environment container |
| `CHROMA_URL`           | Root `.env`              | `ai-service`        | Server-only                   | Integrasi Chroma masa depan milik AI service; default `http://127.0.0.1:8000` (lokal) / `http://chroma:8000` (VPS)                                                           |
| `DOCS_ENABLED`         | Root `.env`              | `api`, `ai-service` | Server-only                   | Kosong di template → default `true` di dev/test, `false` di produksi (`"true"` / `"false"`)                                                                                  |
| `DOCS_USERNAME`        | Root `.env`              | `api`, `ai-service` | Server-only, rahasia produksi | Kosong di template; wajib diisi saat `DOCS_ENABLED=true` di mode produksi                                                                                                    |
| `DOCS_PASSWORD`        | Root `.env`              | `api`, `ai-service` | Server-only, rahasia produksi | Kosong di template; wajib **>= 32 karakter** saat `DOCS_ENABLED=true` di mode produksi                                                                                       |
| `WORKER_HOST`          | Root `.env`              | `worker`            | Server-only                   | Host listener liveness worker native; default `127.0.0.1` (`0.0.0.0` di container VPS)                                                                                       |
| `WORKER_PORT`          | Root `.env`              | `worker`            | Server-only                   | Port listener liveness worker native; default `3002`, integer 1–65535 (`3002` di container VPS)                                                                              |

Catatan penting implementasi runtime:

- **Pemetaan listener `api` (`API_HOST` & `API_PORT`)**: Saat menjalankan `dev:api`, launcher meneruskan `-H <API_HOST> -p <API_PORT>` ke Next CLI. Saat menjalankan `start:api` (server standalone `apps/api/.next/standalone/apps/api/server.js`), launcher memetakan `API_HOST` → `HOSTNAME` dan `API_PORT` → `PORT` secara internal serta mengabaikan `HOSTNAME`/`PORT` warisan shell agar listener tidak salah mengikat alamat mesin. Di container VPS, `HOSTNAME=0.0.0.0` dan `PORT=3001` ditetapkan secara tetap oleh Dockerfile/Compose.
- **Pemetaan listener `ai-service` (`AI_HOST` & `AI_PORT`) dan isolasi Python**: Launcher Node membaca `AI_HOST` (default `127.0.0.1`) dan `AI_PORT` (default `8001`) untuk menyusun argumen CLI `uv run --frozen uvicorn app.main:app --host <AI_HOST> --port <AI_PORT> [--reload] --no-access-log`. Sementara itu, `apps/ai-service/app/config.py` mencari root `.env` melalui rantai `Path.parent` yang aman di dalam image Docker (tanpa fallback ke `apps/ai-service/.env`), hanya mengambil key milik `AppSettings` (`APP_ENV`, `CHROMA_URL`, `DOCS_ENABLED`, `DOCS_USERNAME`, `DOCS_PASSWORD`), menggunakan `interpolate=False`, dan tidak memutasi `os.environ`.
- **Isolasi ketat `worker`**: Launcher hanya meneruskan `NODE_ENV`, `WORKER_HOST`, dan `WORKER_PORT` ke proses worker. Kredensial `DATABASE_URL`, `WAHA_API_KEY`, `DOCS_PASSWORD`, `AI_SERVICE_URL`, maupun `CHROMA_URL` di root `.env` tidak pernah diekspos ke environment worker.
- **Prisma CLI offline (`packages/db/prisma.config.ts`)**: Prisma tooling membaca `DATABASE_URL` dari `process.env` atau langsung dari root `.env` melalui `util.parseEnv` tanpa mutasi global. Jika `DATABASE_URL` kosong atau root `.env` belum ada, `prisma.config.ts` menyediakan fallback URL sintaktis **hanya untuk command `generate` dan `validate`** (tanpa membuka koneksi jaringan). Command Prisma lain seperti migrasi tetap mewajibkan `DATABASE_URL` eksplisit.
- **Forwarding Turborepo dan filter profil startup**: `turbo.json` meneruskan `UV_*` secara global serta daftar pass-through (`NODE_ENV`, `API_HOST`, `API_PORT`, `DATABASE_URL`, `AI_HOST`, `AI_PORT`, `DOCS_ENABLED`, `DOCS_USERNAME`, `DOCS_PASSWORD`, `AI_SERVICE_URL`, `CHROMA_URL`, `WAHA_BASE_URL`, `WAHA_API_KEY`, `WORKER_HOST`, `WORKER_PORT`, `API_BASE_URL`, `NEXT_PUBLIC_APP_NAME`) pada task `dev` dan `start`, kemudian loader startup (`scripts/service-environment.mjs`) memfilter environment terhadap profil allowlist masing-masing layanan.

## Gerbang keamanan dokumentasi (`DOCS_ENABLED`, `DOCS_USERNAME`, `DOCS_PASSWORD`)

Kedua backend (`@smart-catering/api` dan `@smart-catering/ai-service`) menerapkan kebijakan yang sama untuk `/docs` dan endpoint skema OpenAPI (`/api/openapi` pada API, `/openapi.json` pada AI service):

1. **Nilai `DOCS_ENABLED`**:
   - Hanya menerima string `"true"` atau `"false"` (case-insensitive setelah trim). Nilai lain dianggap konfigurasi tidak sah dan gagal tertutup (fail-closed).
   - Bila kosong atau tidak disetel: bernilai default `true` pada mode development/test (`NODE_ENV` != `production` di API; `APP_ENV` != `production` di AI service), dan bernilai default **`false`** pada mode produksi (`NODE_ENV=production` atau `APP_ENV=production`).
2. **Saat dokumentasi nonaktif (`DOCS_ENABLED=false`)**:
   - Request ke `/docs` maupun endpoint skema OpenAPI mengembalikan HTTP `404` RFC 9457 Problem Details (`application/problem+json`) dengan `Cache-Control: private, no-store` dan `Vary: Authorization`.
3. **Saat dokumentasi diaktifkan di produksi (`DOCS_ENABLED=true`)**:
   - Wajib menyetel `DOCS_USERNAME` (tidak kosong) dan `DOCS_PASSWORD` dengan panjang **minimal 32 karakter**.
   - Bila `DOCS_USERNAME` kosong atau `DOCS_PASSWORD` kurang dari 32 karakter di produksi, backend gagal tertutup dengan HTTP `500` Problem Details generik (`"An unexpected error occurred."`) dan tidak pernah mengekspos dokumentasi tanpa autentikasi.
   - Bila terkonfigurasi dengan benar, request wajib menyertakan header `Authorization: Basic <base64(username:password)>` yang diverifikasi secara constant-time (UTF-8). Kredensial yang hilang atau salah menghasilkan HTTP `401` Problem Details beserta header `WWW-Authenticate: Basic realm="Smart Catering Docs", charset="UTF-8"`.
   - Pengaktifan dokumentasi di produksi **wajib berada di balik reverse proxy TLS/HTTPS**. Kredensial dokumentasi hanya diteruskan ke service `api` dan `ai-service`, **tidak pernah** ke `worker` atau `web`.

## Variabel Infrastruktur & Docker Compose di Root (`.env.example` → `.env`)

| Variabel                      | Default pada `.env.example` | Pemakaian pada Compose & runtime native                                                                   |
| ----------------------------- | --------------------------- | --------------------------------------------------------------------------------------------------------- |
| `POSTGRES_USER`               | `smartcatering`             | Role PostgreSQL lokal/VPS                                                                                 |
| `POSTGRES_PASSWORD`           | Kosong                      | **Wajib diisi sebelum Compose**; password DB mentah (bukan percent-encoded)                               |
| `POSTGRES_DB`                 | `smart_catering`            | Nama database PostgreSQL                                                                                  |
| `POSTGRES_PORT`               | `5432`                      | Mapping loopback host dev (`127.0.0.1:5432:5432`); tidak dipublikasikan di VPS                            |
| `DATABASE_URL`                | Kosong                      | URL koneksi PostgreSQL host lokal (`127.0.0.1:5432`) untuk `api` native dan Prisma CLI                    |
| `VPS_DATABASE_URL`            | Kosong                      | **Wajib diisi sebelum Compose VPS** dengan host internal `postgres:5432`; dipetakan ke `DATABASE_URL` API |
| `CHROMA_PORT`                 | `8000`                      | Mapping loopback host dev (`127.0.0.1:8000:8000`); tidak dipublikasikan di VPS                            |
| `CHROMA_URL`                  | `http://127.0.0.1:8000`     | URL Chroma untuk `ai-service` native; Compose VPS menetapkan `http://chroma:8000` secara eksplisit        |
| `WAHA_PORT`                   | `3003`                      | Mapping loopback host dev profile WAHA (`127.0.0.1:3003:3000`); tidak dipublikasikan di VPS               |
| `WAHA_BASE_URL`               | `http://127.0.0.1:3003`     | URL WAHA untuk `api` native; Compose VPS menetapkan `http://waha:3000` secara eksplisit                   |
| `WAHA_API_KEY`                | Kosong                      | **Wajib diisi sebelum semua command Compose**, walau profile `waha` belum diaktifkan                      |
| `API_HOST` / `API_PORT`       | `127.0.0.1` / `3001`        | Listener native `api`; pada Compose VPS, `API_PORT` memetakan host `127.0.0.1:${API_PORT:-3001}:3001`     |
| `AI_HOST` / `AI_PORT`         | `127.0.0.1` / `8001`        | Listener Uvicorn native `ai-service`; container VPS tetap menggunakan `0.0.0.0:8001` internal             |
| `WORKER_HOST` / `WORKER_PORT` | `127.0.0.1` / `3002`        | Listener liveness native `worker`; container VPS tetap menggunakan `0.0.0.0:3002` internal                |
| `AI_SERVICE_URL`              | `http://127.0.0.1:8001`     | URL `ai-service` untuk `api` native; Compose VPS menetapkan `http://ai-service:8001` pada service `api`   |
| `DOCS_ENABLED`                | Kosong                      | Kosong → `true` di dev native, `false` di start produksi native & Compose VPS (`${DOCS_ENABLED:-false}`)  |
| `DOCS_USERNAME`               | Kosong                      | Opsional hingga `DOCS_ENABLED=true`; diteruskan hanya ke `api` dan `ai-service`                           |
| `DOCS_PASSWORD`               | Kosong                      | Opsional hingga `DOCS_ENABLED=true` (wajib >= 32 karakter saat aktif di mode produksi)                    |

Compose menginterpolasi konfigurasi sebelum menyaring profile. Karena `POSTGRES_PASSWORD` dan `WAHA_API_KEY` menggunakan ekspresi required yang fail-closed (`:?`), isi **`POSTGRES_PASSWORD` dan `WAHA_API_KEY`** di root `.env` sebelum menjalankan `npm run infra:config`, `npm run infra:up`, maupun command Compose lainnya. Untuk command Compose **VPS**, isi juga **`VPS_DATABASE_URL`** lengkap dengan host `postgres:5432` dan password yang sesuai.

## Membuat dan menyamakan secret

Buat nilai acak untuk password DB, key WAHA, dan (bila dokumentasi produksi diaktifkan) `DOCS_PASSWORD` **secara terpisah**:

```sh
node -e "console.log(require('node:crypto').randomBytes(32).toString('hex'))"
```

Output hex 64 karakter di atas memenuhi syarat minimal 32 karakter untuk `DOCS_PASSWORD` dan aman digunakan pada URL tanpa karakter khusus. `POSTGRES_PASSWORD` harus tetap berupa password **mentah**. Percent-encode komponen username/password **hanya di connection URL** (`DATABASE_URL` atau `VPS_DATABASE_URL`), bukan seluruh URL atau nilai `POSTGRES_PASSWORD`.

## Boundary keamanan dan deployment

- `NEXT_PUBLIC_*` masuk ke browser; jangan beri prefix itu pada URL DB, URL internal AI service, atau secret/key provider/dokumentasi.
- Jangan memberikan `DATABASE_URL`, `VPS_DATABASE_URL`, `CHROMA_URL`, `AI_SERVICE_URL`, `WAHA_API_KEY`, atau `DOCS_PASSWORD` ke project Vercel web.
- Worker Fase 0 hanya menerima `NODE_ENV`, `WORKER_HOST`, dan `WORKER_PORT`; tidak menerima kredensial DB, WAHA, maupun `DOCS_*`.
- Gunakan `npm run infra:config` atau `docker compose --env-file .env -f infra/docker/compose.dev.yaml config --quiet` untuk validasi tanpa mencetak secret.

Lihat [development](development.md) untuk menjalankan proses dan [VPS](deployment-vps.md) untuk env internal. Runtime Docker dan hasil pemeriksaan tetap mengikuti [batas bukti](README.md#status-dan-batas-bukti).
