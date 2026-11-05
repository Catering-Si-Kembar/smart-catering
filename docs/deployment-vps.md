# Deployment VPS — API, AI service, worker, dan infrastruktur internal

**Diperbarui:** 2026-11-05 · **Status:** prosedur target; belum ada klaim deployment/container runtime berhasil

## Layanan dan prasyarat

VPS menjalankan **API Next.js standalone (`:3001`)**, **AI service Python/FastAPI (`:8001`)**, **worker Node.js independen (`:3002`)**, **PostgreSQL (`:5432`)**, dan **Chroma (`:8000`)**. **WAHA (`:3000`)** diaktifkan hanya melalui profile opsional `waha`. Web tetap di Vercel. Redis + BullMQ hanya opsi masa depan, tidak ada pada Compose/dependency fase ini; tidak ada integrasi Telegram.

Operator perlu menyiapkan VPS Linux yang sesuai arsitektur image, Git/access checkout atau distribusi source yang disetujui, Docker Engine dan Compose v2, storage persistent, secret, backup, firewall, dan reverse proxy TLS **di luar Compose ini**. Tidak ada penyedia VPS, IP, domain, akun SSH, nama repository, atau lokasi direktori deploy yang diasumsikan.

## File dan build context

- `infra/docker/compose.vps.yaml`: layanan `postgres`, `chroma`, `api`, `ai-service`, `worker`, serta `waha` pada profile opsional.
- `infra/docker/api.Dockerfile`: build dari **root repository** menggunakan `node:24.15.0-alpine3.23@sha256:d1b3b4da11eefd5941e7f0b9cf17783fc99d9c6fc34884a665f40a06dbdfc94f`. Menyalin keenam manifest `package.json` workspace (termasuk wrapper `apps/ai-service/package.json`) agar `npm ci` memvalidasi satu `package-lock.json` root tanpa membutuhkan Python di dalam image Node. Membangun `@smart-catering/types`, `@smart-catering/db`, dan `@smart-catering/api` standalone (`DOCS_ENABLED=false` secara default); runtime non-root (`USER node`).
- `infra/docker/ai-service.Dockerfile`: build dari **root repository** menggunakan image resmi **`python:3.12.16-slim-bookworm@sha256:e697c81897302a4c4333bade000d98038fbb21eb064f8ee1fd42d02ebcd9d337`**. Memasang **`uv==0.13.7`**, menyalin `apps/ai-service/{pyproject.toml,uv.lock,.python-version}` serta `apps/ai-service/app`, lalu menjalankan **`uv sync --frozen --no-dev`** tanpa extras `rag`/`ml`. Berjalan sebagai user non-root `aiservice` (UID `10001`) dengan `APP_ENV=production`, `DOCS_ENABLED=false`, dan command `uvicorn app.main:app --host 0.0.0.0 --port 8001`.
- `infra/docker/worker.Dockerfile`: build dari **root repository** menggunakan base image Node yang sama, menyalin keenam manifest `package.json` workspace untuk `npm ci`, lalu hanya membangun `@smart-catering/types` dan `@smart-catering/worker` secara independen dari `apps/api` dan `apps/ai-service`; runtime non-root (`USER node`) menjalankan `apps/worker/dist/index.js`.
- `.dockerignore`: mencegah env nyata, `node_modules`, `.venv`, `__pycache__`, cache pytest/mypy/ruff, dan output build lokal masuk ke build context Docker.

Install build Node memakai kebijakan npm12 `allowScripts` root: hanya `prisma@7.10.1`, `@prisma/engines@7.10.1`, dan `esbuild@0.28.2` disetujui secara exact.

## Environment sebelum menjalankan Compose

Dari root checkout yang benar pada VPS:

```sh
cp .env.example .env
```

Jangan overwrite `.env` yang sudah ada. Isi **`POSTGRES_PASSWORD` dan `WAHA_API_KEY`** dengan nilai acak kuat yang berbeda, serta **`VPS_DATABASE_URL`** sebagai connection URL internal lengkap sebelum command Compose VPS.

| Layanan Compose | Variabel runtime yang diteruskan                                                                                                                                                                                                                                                                           | Tujuan dan batas keamanan                                                                                                                                                               |
| --------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `api`           | `NODE_ENV=production`, `PORT=3001`, `HOSTNAME=0.0.0.0`, `DATABASE_URL` (dari `VPS_DATABASE_URL`), `AI_SERVICE_URL=http://ai-service:8001`, `WAHA_BASE_URL=http://waha:3000`, `WAHA_API_KEY`, `DOCS_ENABLED=${DOCS_ENABLED:-false}`, `DOCS_USERNAME=${DOCS_USERNAME:-}`, `DOCS_PASSWORD=${DOCS_PASSWORD:-}` | Hanya `api` yang dipublikasikan ke loopback host `127.0.0.1:${API_PORT:-3001}:3001`. `AI_SERVICE_URL` adalah konfigurasi masa depan tanpa panggilan aktif/ketergantungan startup Fase 0 |
| `ai-service`    | `APP_ENV=production`, `CHROMA_URL=http://chroma:8000`, `DOCS_ENABLED=${DOCS_ENABLED:-false}`, `DOCS_USERNAME=${DOCS_USERNAME:-}`, `DOCS_PASSWORD=${DOCS_PASSWORD:-}`                                                                                                                                       | Hanya jaringan container internal (`:8001`); pemilik resmi `CHROMA_URL`. Tidak menerima `DATABASE_URL` atau `WAHA_API_KEY`                                                              |
| `worker`        | `NODE_ENV=production`, `WORKER_HOST=0.0.0.0`, `WORKER_PORT=3002`                                                                                                                                                                                                                                           | Hanya jaringan container internal (`:3002`). Tidak menerima `DATABASE_URL`, `WAHA_API_KEY`, `CHROMA_URL`, `AI_SERVICE_URL`, maupun `DOCS_*`                                             |

### Kebijakan dokumentasi OpenAPI/Scalar di VPS (`DOCS_ENABLED`)

- Pada `.env.example`, `DOCS_ENABLED` dikosongkan secara default, sementara mode produksi aplikasi dan ekspresi `${DOCS_ENABLED:-false}` pada `compose.vps.yaml` menetapkan nilai default **`false`**. Dalam kondisi ini, `/docs` dan endpoint skema (`/api/openapi` pada `api`, `/openapi.json` pada `ai-service`) tertutup rapat dan mengembalikan HTTP `404` Problem Details.
- Jika operator perlu mengaktifkan dokumentasi di VPS (`DOCS_ENABLED=true`):
  1. Pastikan akses eksternal berada di balik **reverse proxy TLS/HTTPS**.
  2. Setel `DOCS_USERNAME` dan `DOCS_PASSWORD` (wajib **minimal 32 karakter**, misalnya 64 karakter hex acak) di `.env`.
  3. Bila `DOCS_ENABLED=true` pada mode produksi tetapi `DOCS_USERNAME` kosong atau `DOCS_PASSWORD` kurang dari 32 karakter, `api` dan `ai-service` gagal tertutup (fail-closed) dengan HTTP `500` Problem Details generik dan tidak pernah menampilkan dokumentasi ke publik.
  4. Kredensial `DOCS_USERNAME` dan `DOCS_PASSWORD` hanya diteruskan ke `api` dan `ai-service`, tidak ke `worker`.

## Start, pemeriksaan, dan stop

Prosedur ini dijalankan oleh operator pada lingkungan ber-Docker setelah izin deploy diberikan. Seluruh command dari root checkout:

```sh
docker compose --env-file .env -f infra/docker/compose.vps.yaml config --quiet
docker compose --env-file .env -f infra/docker/compose.vps.yaml up -d --build
docker compose --env-file .env -f infra/docker/compose.vps.yaml ps
curl --fail http://127.0.0.1:3001/health
docker compose --env-file .env -f infra/docker/compose.vps.yaml exec ai-service python -c "import sys, urllib.request; r = urllib.request.urlopen('http://127.0.0.1:8001/health', timeout=4); print(r.read().decode()); sys.exit(0 if r.status == 200 else 1)"
docker compose --env-file .env -f infra/docker/compose.vps.yaml exec worker node -e "fetch('http://127.0.0.1:3002/health').then(r=>{if(!r.ok)process.exitCode=1;return r.text()}).then(console.log).catch(()=>process.exitCode=1)"
docker compose --env-file .env -f infra/docker/compose.vps.yaml exec postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT 1;"'
```

Respons liveness yang diharapkan:

- **API (`http://127.0.0.1:3001/health`)**: HTTP 200 `{"data":{"status":"ok","service":"api"},"meta":{"requestId":"<uuid>"}}` beserta header `X-Request-Id`.
- **AI Service (internal `:8001/health`)**: HTTP 200 `{"data":{"status":"ok","service":"ai-service"},"meta":{"requestId":"<uuid>"}}` beserta header `X-Request-Id`.
- **Worker (internal `:3002/health`)**: HTTP 200 `{"status":"ok","service":"worker"}` (liveness internal Node.js).

Ketiganya adalah liveness proses, bukan readiness DB/Chroma/WAHA. Chroma tetap memakai healthcheck `/api/v2/heartbeat`, dan WAHA tetap `/ping`.

Aktifkan WAHA hanya jika diperlukan untuk pekerjaan infrastruktur yang disetujui:

```sh
docker compose --env-file .env -f infra/docker/compose.vps.yaml --profile waha up -d --build
```

Stop tanpa menghapus data:

```sh
docker compose --env-file .env -f infra/docker/compose.vps.yaml --profile waha down
```

Jangan menambahkan `-v`/`--volumes` pada shutdown normal. Named volumes menyimpan PostgreSQL, Chroma, dan sesi/file WAHA; operator tetap wajib membuat dan menguji backup/restore.

## Isolasi jaringan dan HTTPS

| Service      | Publikasi host VPS                            |
| ------------ | --------------------------------------------- |
| `api`        | Hanya `127.0.0.1:${API_PORT:-3001}:3001`      |
| `ai-service` | Tidak ada; port 8001 hanya jaringan container |
| `worker`     | Tidak ada; port 3002 hanya jaringan container |
| `postgres`   | Tidak ada host port                           |
| `chroma`     | Tidak ada host port                           |
| `waha`       | Tidak ada host port, profile opt-in           |

Reverse proxy host yang dikelola operator meneruskan HTTPS ke API loopback (`127.0.0.1:3001`). Layanan `ai-service` tidak dipublikasikan ke internet; pada fase mendatang, hanya `api` yang memanggil `http://ai-service:8001` melalui jaringan internal Docker. Jangan memakai hostname `postgres`, `chroma`, `ai-service`, atau `waha` dari Vercel karena nama tersebut hanya berlaku di DNS jaringan Docker VPS.

### Batas HTTP sebelum handler aplikasi

Response helpers menstandarkan error aplikasi, bukan penolakan transport yang terjadi sebelum Route Handler/ASGI menerima request. Probe pada server Next.js standalone menemukan `TRACE /health` menghasilkan HTTP `500 text/plain` karena `NextRequestAdapter` menolak metode tersebut sebelum membentuk `Request`; tidak ada stack trace dalam respons klien. Next Proxy juga menerima `NextRequest`, sehingga bukan perbaikan yang tepat untuk tahap ini.

Operator reverse proxy wajib mengizinkan hanya metode aplikasi (`GET`, `HEAD`, `POST`, `PUT`, `PATCH`, `DELETE`, `OPTIONS`) dan menolak `TRACE`, `CONNECT`, `TRACK`, serta metode lain sebelum upstream Next.js. TLS, pembatasan metode, dan batas ukuran header/body merupakan tanggung jawab edge VPS; konfigurasi tersebut perlu diuji di VPS nyata. Jangan memodifikasi internal Next.js atau menambahkan custom server hanya untuk menyamarkan batas framework ini.

Untuk proses native di luar Compose, launcher `npm run start:ai` (serta `start:backend` dan `start:all`) otomatis menyetel `APP_ENV=production`, menonaktifkan reload, dan mengikat `AI_HOST`:`AI_PORT` dari root `.env` (jika menjalankan Uvicorn secara langsung tanpa launcher npm, setel `APP_ENV=production` secara eksplisit). Di dalam container VPS, image tidak menyalin `.env` host dan layanan hanya menerima variabel `environment` eksplisit dari Dockerfile/Compose dengan port internal tetap (`api` `:3001`, `ai-service` `:8001`, `worker` `:3002`).

### Privasi log

Entrypoint Uvicorn development, native, dan Docker menggunakan `--no-access-log`: access log bawaan mencatat query string mentah dan dapat membocorkan token di URL. Error logging aplikasi tetap aktif dengan status, requestId, pathname, dan jenis error; tidak mencatat pesan exception, stack, body, header autentikasi, query string, atau kredensial. Atur log reverse proxy dengan kebijakan yang sama: gunakan pathname terpisah dari query string dan jangan mencatat `Authorization`.

## Pembaruan dan rollback

Deploy commit yang ditinjau, simpan identitas commit/image/config tanpa mencatat secret, lalu build/up dan ulangi health checks untuk `api`, `ai-service`, `worker`, `postgres`, dan `chroma`. Simpan artefak/commit sebelumnya untuk rollback aplikasi. Jangan menghapus volume saat rollback.

## Referensi

- [Docker Compose — env interpolation](https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/)
- [Next.js — standalone dan monorepo tracing](https://nextjs.org/docs/app/api-reference/config/next-config-js/output)
- [uv — Using uv in Docker](https://docs.astral.sh/uv/guides/integration/docker/)
- [Arsitektur](architecture.md) · [ADR](decisions/README.md) · [Batas bukti](README.md#status-dan-batas-bukti)
