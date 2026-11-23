# Spesifikasi Teknis: DevOps & Infrastruktur (`04-devops-infra.md`)

Berkas ini memuat spesifikasi teknis lengkap untuk 5 issue area DevOps & Infrastruktur (`OPS-01` s.d. `OPS-05`) mencakup tata kelola Git/PR dan CI/CD GitHub Actions dengan proteksi rahasia, provisioning Docker Compose produksi pada VPS Ubuntu dengan reverse proxy HTTPS terisolasi, deployment frontend Next.js di platform Vercel, penyajian SLM/vLLM serverless di Modal GPU, serta automasi cron worker, backup database, dan uji failover pra-demonstrasi.

---

## [OPS-01] Tata Kelola Git/PR, GitHub Actions CI & Secrets Hygiene

- **Labels:** `area:devops`, `priority:P0-blocker`, `quest:main`, `quest:side`
- **Priority:** `P0-blocker`
- **Milestone:** `M1 (21–27 Nov 2026)`
- **Target Path:** `.github/workflows`, `scripts`

### Context

Pengembangan monorepo melibatkan kolaborasi multi-disiplin (Full-Stack, Data Science, AI Engineering). Tanpa otomatisasi pengujian dan tata kelola kode yang disiplin, integrasi kode berisiko menimbulkan regresi tipe, format kode berantakan, serta kebocoran kredensial rahasia (seperti API key LLM, token database, atau password). Sesuai batasan proyek dan rubrik Main Quest, repositori wajib dikelola secara privat di platform GitHub dengan alur kerja Pull Request (PR) terstandarisasi. Dibangun pipeline continuous integration (CI) menggunakan GitHub Actions yang secara otomatis menjalankan typecheck TypeScript dan Python, validasi skema Prisma, unit testing (Vitest dan pytest), linting kode, format checking Prettier, serta pemindaian pencegahan kebocoran berkas rahasia (_secrets hygiene_).

### Scope

**In-Scope:**

- Konfigurasi alur kerja CI pada `.github/workflows/ci.yml` yang terpicu pada setiap push ke branch `dev` dan setiap pembukaan Pull Request.
- Setup matrix pekerjaan CI:
  - Node.js pipeline: `npm run format:check`, `npm run lint`, `npm run db:validate`, `npm run typecheck`, dan `npm test`.
  - Python pipeline: linting Ruff, pemeriksaan tipe Mypy, dan eksekusi pytest pada `apps/ai-service`.
- Template Pull Request (`.github/pull_request_template.md`) dengan checklist pengujian mandiri dan kepatuhan batasan proyek.
- Aturan branch protection pada branch `dev` (wajib lulus seluruh check CI sebelum merge).
- Mekanisme deteksi rahasia lokal dan CI (`scripts/check-secrets.py` atau aturan pemindaian git) untuk memblokir commit yang memuat pola `.env`, token rahasia, atau kredensial database.

**Out-of-Scope:**

- Deployment otomatis (_Continuous Deployment_) ke server VPS produksi dari CI publik (deployment VPS dioperasikan secara semi-otomatis melalui SSH terkontrol pada `OPS-02`).
- Pengujian performa beban tinggi (_load testing_) skala enterprise.

### Business Rules

- Dilarang keras melakukan commit atau membagikan kata sandi, token akses, API key, `DATABASE_URL`, atau data pribadi nyata ke dalam repositori git.
- Seluruh merge ke branch `dev` wajib melalui mekanisme Pull Request dengan status build CI berwarna hijau (seluruh pengujian lulus 100%).
- Berkas data mentah UMKM (`data/raw/*`) dan berkas konfigurasi lokal (`.env`, `apps/web/.env`) wajib diabaikan secara ketat oleh `.gitignore`.

### API Contract

Tidak berlaku (tugas non-API). Mengonfigurasi pipeline otomasi GitHub Actions dan skrip validasi repositori.

### Acceptance Criteria

- [ ] Berkas alur kerja GitHub Actions `.github/workflows/ci.yml` aktif dan tervalidasi sintaksisnya.
- [ ] Seluruh tahapan pipeline (format check, linting, validasi skema DB, typecheck, dan automated tests) tereksekusi secara deterministik.
- [ ] Skrip pemindai rahasia berhasil mendeteksi dan mencegah commit berkas kredensial sensitif.
- [ ] Tersedia panduan kontribusi dan template Pull Request yang memuat daftar periksa guardrail proyek.
- [ ] Eksekusi CI pada runner Ubuntu berjalan efisien dengan memanfaatkan caching dependensi npm dan uv/pip.

### Technical Notes

- Pengaturan cache dependensi npm (`package-lock.json`) dan Python uv (`uv.lock`) di GitHub Actions runner `[Perlu Konfirmasi Tim]`.
- Penetapan minimal 1 persetujuan peninjau (_peer review approval_) pada aturan branch protection GitHub `[Perlu Konfirmasi Tim]`.

### DoD

- [ ] Berkas alur kerja CI tersimpan di `.github/workflows/`.
- [ ] Pengujian simulasi PR berhasil memicu build CI dan menghasilkan status sukses (hijau).
- [ ] Aturan perlindungan repositori terdokumentasi lengkap.

### Dependencies

- Prasyarat: Konfigurasi root monorepo `turbo.json`, `package.json`, dan file konfigurasi linter/prettier.
- Terkait: Menjadi pintu gerbang pengujian otomatis bagi seluruh issue implementasi kode (`FS-*`, `DS-*`, `AI-*`, `OPS-*`).

---

## [OPS-02] Docker Compose Produksi & Provisioning VPS + Reverse Proxy HTTPS

- **Labels:** `area:devops`, `priority:P1-mvp`, `quest:main`, `quest:side`
- **Priority:** `P1-mvp`
- **Milestone:** `M2 (28 Nov–4 Des 2026)`
- **Target Path:** `infra/docker`

### Context

Layanan backend katering terdiri dari Express API (`apps/api`), AI Service FastAPI (`apps/ai-service`), database PostgreSQL 17 (`packages/db`), vector store ChromaDB, background worker pengingat (`apps/worker`), serta kontainer integrasi WhatsApp (WAHA). Seluruh layanan ini dijalankan secara terorkestrasi pada satu unit Virtual Private Server (VPS) Ubuntu 24.04 LTS. Untuk memastikan isolasi lingkungan, efisiensi sumber daya CPU/RAM, dan keamanan data, diperlukan konfigurasi Docker Compose produksi multi-kontainer (`infra/docker/compose.vps.yaml`). Layanan transaksional internal dilindungi dalam bridge network terisolasi tanpa mempublikasikan port internal ke internet, sementara akses publik diamankan melalui reverse proxy (seperti Caddy atau Nginx) yang mengelola sertifikat TLS/HTTPS otomatis dari Let's Encrypt.

### Scope

**In-Scope:**

- Pembuatan dan optimasi Dockerfile produksi multi-stage:
  - `infra/docker/api.Dockerfile` untuk Express backend.
  - `infra/docker/ai-service.Dockerfile` untuk FastAPI Python.
  - `infra/docker/worker.Dockerfile` untuk Node.js worker daemon.
- Penyempurnaan konfigurasi `infra/docker/compose.vps.yaml` dengan alokasi network `smart_catering_vps_net` dan volume persisten untuk PostgreSQL, ChromaDB, dan sesi WAHA.
- Konfigurasi pemeriksaan kesehatan (_healthcheck_) pada setiap service dengan parameter `interval`, `timeout`, dan `retries` teruji.
- Setup konfigurasi reverse proxy HTTPS (Caddy/Nginx) pada port 80 dan 443 yang mengarahkan lalu lintas `/api/*` ke Express (`:3001`).
- Pengamanan isolasi port: PostgreSQL (`:5432`), ChromaDB (`:8000`), dan FastAPI (`:8001`) tidak dipublikasikan ke antarmuka publik host (`127.0.0.1` atau internal network only).
- Skrip bantuan manajemen kontainer pada VPS (`infra/docker/` scripts).

**Out-of-Scope:**

- Hosting frontend Next.js di VPS (frontend dideploy terpisah di Vercel pada `OPS-03`).
- Klaster multi-node Kubernetes atau Docker Swarm (melebihi kebutuhan MVP UMKM).

### Business Rules

- Port database PostgreSQL dan endpoint FastAPI dilarang keras dibuka ke IP publik internet tanpa enkripsi dan autentikasi.
- Seluruh container produksi wajib memiliki kebijakan restart otomatis (`restart: unless-stopped`).
- Semua kredensial dan kata sandi produksi wajib dibaca melalui variabel lingkungan file `.env` di VPS, dilarang disematkan langsung di dalam file compose.

### API Contract

Tidak berlaku (tugas non-API). Mengonfigurasi lingkungan runtime kontainer VPS dan reverse proxy yang menyajikan rute publik HTTPS `/api/v1/*`.

### Acceptance Criteria

- [ ] Perintah `docker compose -f infra/docker/compose.vps.yaml config` memvalidasi konfigurasi tanpa sintaks error.
- [ ] Seluruh kontainer (`postgres`, `chroma`, `api`, `ai-service`, `worker`, `waha`) berhasil dibangun dan berjalan dalam status `healthy`.
- [ ] Endpoint reverse proxy publik HTTPS merespons request dan meneruskannya ke backend Express secara transparan.
- [ ] Volume persisten PostgreSQL dan ChromaDB berhasil mempertahankan data transaksi saat kontainer di-restart.
- [ ] Port internal basis data dan AI service terbukti tidak dapat diakses langsung dari jaringan luar.

### Technical Notes

- Spesifikasi kapasitas sumber daya VPS minimum: 2 vCPU, 4 GB RAM, dan 40 GB SSD `[Perlu Konfirmasi Tim]`.
- Penetapan domain atau subdomain resmi VPS (contoh: `api.catering-sikembar.my.id`) untuk penerbitan sertifikat SSL Caddy `[Perlu Konfirmasi Tim]`.

### DoD

- [ ] Seluruh berkas Dockerfile dan compose produksi tersimpan rapi di direktori `infra/docker/`.
- [ ] Uji coba provisioning pada server VPS berhasil dilakukan dan diverifikasi dengan healthcheck.
- [ ] Dokumentasi panduan operasional deployment VPS tercatat dalam berkas dokumentasi infrastruktur.

### Dependencies

- Prasyarat: `FS-02` (Skema Prisma), `FS-03` (Express API), `AI-01` (FastAPI Service).
- Terkait: Menjadi fondasi infrastruktur runtime untuk `FS-04`..`FS-08`, `AI-02`..`AI-07`, dan `OPS-05`.

---

## [OPS-03] Deployment Frontend Vercel & Verifikasi Koneksi BFF Desktop/Mobile

- **Labels:** `area:devops`, `priority:P1-mvp`, `quest:main`, `quest:side`
- **Priority:** `P1-mvp`
- **Milestone:** `M2 (28 Nov–4 Des 2026)`
- **Target Path:** `apps/web`

### Context

Aplikasi web Catering Si Kembar (`apps/web`) dibangun menggunakan Next.js App Router dan ditargetkan untuk dideploy pada platform serverless hosting gratis Vercel (free tier). Sesuai arsitektur sistem, frontend mengadopsi pola Backend-For-Frontend (BFF) internal di mana rute API Next.js (`apps/web/app/api/*`) bertindak sebagai proxy aman yang meneruskan panggilan ke backend Express VPS (`API_BASE_URL`). Hal ini menjaga agar secret server tidak bocor ke browser client. Tim DevOps bertugas mengonfigurasi proyek Vercel dalam struktur monorepo Turbo, menetapkan variabel lingkungan produksi, mengonfigurasi header CORS dan keamanan, serta melakukan verifikasi koneksi end-to-end antara Vercel dan VPS melalui pengujian langsung pada peramban web desktop dan perangkat telepon seluler.

### Scope

**In-Scope:**

- Konfigurasi build monorepo di dasbor Vercel: pemilihan Root Directory `apps/web`, build command `turbo run build --filter=@smart-catering/web`, dan output directory `.next`.
- Pengaturan variabel lingkungan produksi di Vercel: `API_BASE_URL` (URL HTTPS publik Express VPS), `NEXT_PUBLIC_APP_URL`, dan token pendukung.
- Verifikasi header keamanan HTTP (CSP, X-Content-Type-Options, X-Frame-Options) dan pengaturan CORS backend VPS agar mengizinkan domain Vercel.
- Pengujian keterjangkauan dan responsivitas aplikasi web secara langsung melalui jaringan seluler nyata pada perangkat ponsel Android/iOS (resolusi target `390x844`) dan layar desktop (`1440x900`).
- Pengujian skenario kegagalan jaringan: tampilan pesan error informatif pada UI ketika koneksi internet terputus atau server backend tidak merespons.

**Out-of-Scope:**

- Penggunaan custom domain berbayar (cukup memanfaatkan domain bawaan gratis `*.vercel.app` selama masa demonstrasi proyek).
- Pembuatan aplikasi native mobile (Android APK / iOS IPA) karena proyek difokuskan pada web responsif.

### Business Rules

- Aplikasi web wajib dapat dibuka langsung melalui tautan peramban internet tanpa mewajibkan pengguna melakukan instalasi perangkat lunak atau menjalankan kode lokal.
- Variabel lingkungan rahasia server dilarang menggunakan prefix `NEXT_PUBLIC_` agar tidak terpapar ke bundle JavaScript browser.
- Panggilan API dari browser client dilarang memanggil port raw atau IP mentah VPS secara langsung tanpa protokol HTTPS.

### API Contract

Tidak berlaku (tugas non-API). Menghasilkan URL publik Vercel aktif berprotokol HTTPS yang terhubung ke backend Express.

### Acceptance Criteria

- [ ] Deployment otomatis Vercel berhasil terpicu dan sukses setiap kali terjadi merge ke branch `dev` (atau branch rilis yang ditetapkan tim `[Perlu Konfirmasi Tim]`).
- [ ] Halaman login dan dashboard aplikasi web termuat dengan sempurna di URL produksi Vercel.
- [ ] Panggilan Axios BFF `/api/*` dari Next.js berhasil berkomunikasi dengan backend Express di VPS tanpa kendala CORS.
- [ ] Aplikasi web lolos uji tampilan responsif pada peramban mobile layar sasaran `390x844` dan desktop `1440x900` (tampilan navigasi pas, tombol sentuh minimal 44px, tanpa horizontal scrollbar).
- [ ] Waktu muat awal (_First Contentful Paint_) pada jaringan 4G tercapai di bawah 3 detik.

### Technical Notes

- Nama proyek Vercel dan pengikatan repositori GitHub `[Perlu Konfirmasi Tim]`.
- Penyelarasan whitelist domain Vercel preview pada middleware CORS Express backend `[Perlu Konfirmasi Tim]`.

### DoD

- [ ] Aplikasi web aktif dan dapat diakses publik melalui tautan Vercel resmi.
- [ ] Pengujian akses mobile layar `390x844` dan desktop `1440x900` terbukti sukses dan didokumentasikan.
- [ ] Pipeline continuous deployment Vercel berjalan stabil tanpa build error.

### Dependencies

- Prasyarat: `FS-01` (App Mockup & Shell Web), `OPS-02` (Reverse Proxy HTTPS VPS).
- Terkait: Menjadi platform demonstrasi langsung bagi pengujian pengguna dan demonstrasi skenario akhir pada `FS-09`.

---

## [OPS-04] Deployment SLM/LLM Open-Source di Modal GPU (vLLM)

- **Labels:** `area:devops`, `priority:P2-side-quest`, `quest:side`
- **Priority:** `P2-side-quest`
- **Milestone:** `M3 (5–11 Des 2026)`
- **Target Path:** `infra/modal`

### Context

Untuk mendapatkan nilai tambah maksimal pada rubrik Side Quest Gen AI melalui penyajian model bahasa kecil (_Small Language Model_) atau LLM terbuka yang di-host mandiri, tim memanfaatkan infrastruktur serverless GPU Modal. Layanan ini menyajikan inferensi model berbobot terbuka (seperti Qwen2.5-7B-Instruct atau Llama-3.2-3B) menggunakan engine serving berkinerja tinggi **vLLM**. Model ini dialokasikan untuk menghasilkan analisis naratif laporan keuangan dan operasional (_AI Business Insight_) yang dipanggil oleh layanan AI (`apps/ai-service`). Tim DevOps bertugas menyusun konfigurasi aplikasi Modal di direktori `infra/modal/`, mengatur alokasi jenis GPU yang hemat biaya (NVIDIA T4 atau A10G), mengonfigurasi cold-start dan mekanisme auto-suspend untuk menghemat kredit gratis, mengamankan endpoint dengan bearer auth token, serta menguji latensi inferensi.

### Scope

**In-Scope:**

- Pembuatan skrip deployment serverless di `infra/modal/serve_vllm.py` menggunakan SDK Python Modal.
- Pengaturan container image Modal: instalasi PyTorch, dependensi vLLM, dan pengunduhan bobot model dari Hugging Face ke Modal Volume cache.
- Alokasi sumber daya GPU efisien: pemanfaatan GPU NVIDIA T4 (16GB VRAM) atau A10G dengan kuantisasi bobot jika diperlukan.
- Pengaturan siklus hidup serverless: `container_idle_timeout=60` detik (skala ke 0 saat tidak ada permintaan untuk menghemat kredit).
- Proteksi autentikasi endpoint web Modal menggunakan token rahasia pada header `Authorization: Bearer <MODAL_AUTH_TOKEN>`.
- Dokumentasi langkah deployment (`modal run` / `modal deploy`) dan pemantauan pemakaian kredit di `infra/modal/README.md`.
- Dokumentasi kontrak HTTP eksternal vLLM OpenAI-compatible untuk pemanggilan inferensi chat dan healthcheck.

**Out-of-Scope:**

- Pelatihan ulang (_fine-tuning_) bobot LLM (menggunakan model instruct pre-trained yang sudah ada).
- Hosting server GPU mandiri secara fisik di tempat (_on-premise_).

### Business Rules

- Endpoint inferensi GPU dilarang dibuka untuk umum tanpa autentikasi bearer token rahasia.
- Kontainer GPU wajib memiliki batasan idle timeout ketat agar kredit komputasi gratis Modal tidak habis terbuang saat sistem tidak digunakan.
- Token autentikasi dan API key Modal dilarang di-commit ke repositori git; seluruh kredensial dikelola via Modal Secrets atau environment lokal.

### API Contract

#### Daftar Endpoint

| Method | Path                                                            | Fungsi                                                                          | Autentikasi / Role                                      |
| :----- | :-------------------------------------------------------------- | :------------------------------------------------------------------------------ | :------------------------------------------------------ |
| `POST` | `https://<workspace>--vllm-serve.modal.run/v1/chat/completions` | Inferensi chat completions kompatibel OpenAI dari model terbuka vLLM            | Autentikasi: `Authorization: Bearer <MODAL_AUTH_TOKEN>` |
| `GET`  | `https://<workspace>--vllm-serve.modal.run/health`              | Pemeriksaan kesiapan (readiness) & kesehatan (liveness) runtime serverless vLLM | Autentikasi: `Authorization: Bearer <MODAL_AUTH_TOKEN>` |

#### Format Wire Contract Sukses (OpenAI-Compatible)

- `POST https://<workspace>--vllm-serve.modal.run/v1/chat/completions`
  - Headers:
    - `Authorization: Bearer <MODAL_AUTH_TOKEN>`
    - `Content-Type: application/json`
  - Request Body (`application/json`, OpenAI Compatible):
    ```json
    {
      "model": "Qwen/Qwen2.5-7B-Instruct",
      "messages": [
        { "role": "system", "content": "Anda adalah asisten analis bisnis katering..." },
        { "role": "user", "content": "Analisis ringkas data omzet katering berikut: ..." }
      ],
      "temperature": 0.3,
      "max_tokens": 512
    }
    ```
  - Success Response (`200 OK`, `application/json`):
    ```json
    {
      "id": "chatcmpl-modal-12345",
      "object": "chat.completion",
      "created": 1732368100,
      "model": "Qwen/Qwen2.5-7B-Instruct",
      "choices": [
        {
          "index": 0,
          "message": {
            "role": "assistant",
            "content": "Berdasarkan data performa, menu Nasi Box Ayam Lengkuas memberikan kontribusi omzet terbesar..."
          },
          "finish_reason": "stop"
        }
      ],
      "usage": {
        "prompt_tokens": 120,
        "completion_tokens": 85,
        "total_tokens": 205
      }
    }
    ```

- `GET https://<workspace>--vllm-serve.modal.run/health`
  - Response `200 OK`:
    ```json
    {
      "status": "healthy"
    }
    ```

#### Standar Error & Kode Status HTTP

Layanan serverless vLLM Modal GPU mengembalikan kode status HTTP:

- `200 OK`: Inferensi atau pemeriksaan kesehatan runtime berhasil.
- `401 Unauthorized`: Bearer token autentikasi tidak valid atau tidak disertakan.
- `422 Unprocessable Content`: Parameter generasi teks tidak valid (misal: max_tokens negatif atau pesan kosong).
- `429 Too Many Requests`: Alokasi konkurensi kontainer GPU terlampaui.
- `503 Service Unavailable`: Kontainer GPU sedang dalam pemuatan bobot model (cold start).
- `504 Gateway Timeout`: Eksekusi komputasi melebihi batas timeout serverless.

Contoh payload error OpenAI-compatible:

```json
{
  "error": {
    "message": "Bearer token autentikasi tidak valid.",
    "type": "invalid_request_error",
    "code": 401
  }
}
```

#### Catatan Arsitektur Servis Eksternal Serverless GPU

Endpoint ini merupakan infrastruktur inferensi serverless GPU eksternal berbasis antarmuka OpenAI-compatible vLLM yang dipanggil oleh `apps/ai-service`. Layanan ini independen dari monorepo internal, tidak menggunakan envelope `{ data, meta }`, dan tidak menyajikan antarmuka Scalar `/docs` internal monorepo.

### Acceptance Criteria

- [ ] Skrip aplikasi Modal `infra/modal/serve_vllm.py` tervalidasi dan siap di-deploy via CLI Modal.
- [ ] Endpoint vLLM berhasil menyajikan model bahasa terbuka dan merespons request chat completion standar OpenAI.
- [ ] Mekanisme proteksi bearer token berhasil menolak akses tanpa kredensial yang sah dengan HTTP 401.
- [ ] Skala kontainer berhasil mengecil ke 0 GPU (_scale-down_) setelah waktu idle terlampaui.
- [ ] Pengujian pemanggilan inferensi dari klien Python di `apps/ai-service` berjalan sukses.

### Technical Notes

- Registrasi akun dan pengikatan kartu/kredit gratis Modal oleh perwakilan tim `[Perlu Konfirmasi Tim]`.
- Pemilihan bobot model SLM yang paling optimal antara Qwen2.5-7B-Instruct vs Llama-3.2-3B pada GPU T4 `[Perlu Konfirmasi Tim]`.

### DoD

- [ ] Berkas skrip deployment dan panduan pengoperasian tersimpan di `infra/modal/`.
- [ ] Pengujian inferensi live pada serverless GPU Modal sukses dilakukan dan dicatat latensinya.
- [ ] Variabel lingkungan endpoint Modal terintegrasi dengan konfigurasi `apps/ai-service`.

### Dependencies

- Prasyarat: `OPS-01` (Tata Kelola Git & Secrets).
- Terkait: Menjadi mesin komputasi bahasa terbuka untuk modul AI Business Insight pada `AI-06`.

---

## [OPS-05] Penjadwalan Cron Worker VPS, Backup DB/Chroma & Uji Failover Pra-Demo

- **Labels:** `area:devops`, `priority:P2-side-quest`, `quest:side`
- **Priority:** `P2-side-quest`
- **Milestone:** `M4 (12–20 Des 2026)`
- **Target Path:** `apps/worker`, `infra/docker`, `scripts`

### Context

Menjelang pelaksanaan demonstrasi simulasi skenario 100 nasi box di hadapan mitra UMKM dan penilai, sistem membutuhkan jaminan keandalan operasional (_system reliability_) dan ketahanan data tingkat tinggi. Background worker (`apps/worker`) yang bertugas memproses antrean pengingat jadwal produksi dapur (H-2, H-1) dan pengingat pelunasan invoice tagihan dijalankan secara terjadwal menggunakan daemon cron sistem VPS (tanpa Redis/BullMQ pada fase MVP). Selain itu, tim DevOps bertanggung jawab menyiapkan skrip pencadangan (_automated backup_) harian untuk database transaksi PostgreSQL (`pg_dump`) dan data vektor ChromaDB ke direktori arsip terkompresi, serta menyelenggarakan simulasi uji failover pra-demo: pengujian perilaku sistem saat VPS di-reboot mendadak, pengujian kontainer yang mengalami crash, dan verifikasi bahwa eksekusi cron ganda tidak memicu pengiriman pesan pengingat duplikat.

### Scope

**In-Scope:**

- Konfigurasi penjadwalan cron pada host VPS Ubuntu (misal: eksekusi setiap 15 menit atau jam tertentu) untuk memicu job worker pengingat.
- Mekanisme liveness server internal worker pada port `:3002/health` untuk pemantauan uptime oleh Docker Compose.
- Implementasi skrip backup otomatis database PostgreSQL (`scripts/backup-db.sh`) yang menghasilkan dump terenkripsi/terkompresi `.sql.gz` dengan kebijakan retensi minimal 7 hari.
- Implementasi skrip pencadangan arsip data vektor ChromaDB (`scripts/backup-chroma.sh`) dari volume Docker.
- Pelaksanaan uji ketahanan operasional pra-demo:
  1. Simulasi reboot server VPS secara penuh dan verifikasi pemulihan otomatis seluruh kontainer dalam waktu < 60 detik.
  2. Simulasi penghentian paksa kontainer (`docker stop`) dan verifikasi isolasi kegagalan agar layanan lain tidak ikut crash.
  3. Pengujian idempotensi worker: menjalankan cron job dua kali berturut-turut pada interval waktu yang sama untuk memastikan tidak ada duplikasi pesan WhatsApp/email yang terkirim ke staf.
- Penyusunan lembar ceklis failover pra-demonstrasi di dokumen infrastruktur.

**Out-of-Scope:**

- Setup multi-region active-active database replication.
- Langganan layanan cloud storage berbayar pihak ketiga (arsip backup disimpan pada partisi penyimpanan lokal VPS terpisah).

### Business Rules

- Eksekusi cron worker berulang dilarang keras menimbulkan pengiriman notifikasi pengingat duplikat (_duplicate notification_) kepada staf katering atau pelanggan.
- Proses backup basis data tidak boleh mengunci (_table lock_) transaksi pesanan operasional yang sedang berjalan.
- Seluruh file arsip backup wajib memiliki format penamaan berbasis stempel waktu ISO (misal: `backup_smartcatering_20261215_020000.sql.gz`).

### API Contract

#### Daftar Endpoint

| Method | Path      | Fungsi                                                                 | Autentikasi / Role                              |
| :----- | :-------- | :--------------------------------------------------------------------- | :---------------------------------------------- |
| `GET`  | `/health` | Pemeriksaan liveness & uptime internal daemon worker pada port `:3002` | Tidak ada (Internal Docker Network VPS `:3002`) |

#### Format Response Liveness

- `GET /health`
  - Response `200 OK` (`application/json`):
    ```json
    {
      "status": "ok",
      "service": "worker",
      "uptime_seconds": 86400,
      "last_cron_execution": "2026-12-15T08:00:00Z"
    }
    ```

#### Standar Error & Kode Status HTTP

Layanan internal worker mengembalikan kode status HTTP:

- `200 OK`: Worker sehat dan daemon cron aktif.
- `404 Not Found`: Rute endpoint tidak ditemukan (worker hanya mengekspos rute liveness `/health`).
- `405 Method Not Allowed`: Metode HTTP selain `GET` pada `/health`.
- `500 Internal Server Error`: Kegagalan koneksi internal worker ke database transaksi.

Contoh payload error RFC 9457 (`Content-Type: application/problem+json`):

```json
{
  "type": "https://datatracker.ietf.org/doc/html/rfc9457",
  "title": "Worker Health Failure",
  "status": 500,
  "detail": "Koneksi worker ke database transaksi terputus.",
  "instance": "/health"
}
```

#### Catatan Arsitektur Pengecualian ADR-0004

Sesuai keputusan arsitektur ADR-0004, service `apps/worker` bertindak sebagai background daemon penjadwalan internal, bukan backend API REST bisnis transaksi. Oleh karena itu, endpoint liveness internal `:3002/health` dikecualikan dari kewajiban wire envelope `{ data, meta }` dan dokumentasi Scalar `/docs`. Modul worker tetap sepenuhnya terisolasi dan independen tanpa mengimpor internal `apps/api` maupun `apps/ai-service`.

### Acceptance Criteria

- [ ] Konfigurasi cron job VPS aktif dan mengeksekusi tugas worker sesuai jadwal waktu yang ditentukan.
- [ ] Pengujian pemicuan cron ganda terbukti aman dan idempoten (0 pengingat duplikat terkirim).
- [ ] Skrip backup `backup-db.sh` dan `backup-chroma.sh` berhasil mengekspor data dan lulus uji restorasi (_restore test_).
- [ ] Simulasi reboot VPS membuktikan seluruh layanan (`postgres`, `chroma`, `api`, `ai-service`, `worker`) bangkit kembali secara otomatis dan kembali sehat.
- [ ] Dokumen ceklis uji ketahanan pra-demo selesai diisi dan diverifikasi bersama tim.

### Technical Notes

- Pengaturan izin akses crontab pada OS Ubuntu VPS dan penentuan path folder backup `/var/backups/smart-catering` `[Perlu Konfirmasi Tim]`.
- Penjadwalan jam eksekusi backup pada dini hari (contoh: pukul 02:00 WIB) saat lalu lintas katering nihil `[Perlu Konfirmasi Tim]`.

### DoD

- [ ] Skrip pencadangan dan pemulihan tersimpan di direktori `scripts/` atau `infra/`.
- [ ] Uji failover pra-demo tuntas dieksekusi dengan hasil seluruh kriteria ketahanan terpenuhi.
- [ ] Prosedur pemulihan bencana (_disaster recovery guide_) terdokumentasi rapi.

### Dependencies

- Prasyarat: `OPS-02` (Docker Compose VPS), `FS-09` (Modul Pengingat & E2E), `AI-07` (Integrasi WhatsApp).
- Terkait: Menjadi penopang stabilitas operasional pada demonstrasi akhir skenario 100 nasi box.
