# Spesifikasi Teknis: DevOps & Infrastruktur (`04-devops-infra.md`)

Berkas ini memuat spesifikasi teknis lengkap untuk 5 issue area DevOps & Infrastruktur (`OPS-01` s.d. `OPS-05`) yang telah diselaraskan penuh dengan Asah 2026 Project Plan – A26-CS105, mencakup tata kelola Git/PR & GitHub Actions CI (`workflow_dispatch`), Docker Compose VPS & reverse proxy HTTPS terisolasi, deployment frontend Next.js Vercel, deployment SLM/LLM open-source Modal GPU (vLLM) pada M2, serta penjadwalan cron worker VPS (selesai ≤ akhir M3) dan uji anti-duplikasi/backup/failover pra-demo pada M4.

---

## [OPS-01] Tata Kelola Git/PR, GitHub Actions CI & Secrets Hygiene

- **Labels:** `area:devops`, `priority:P0-blocker`, `quest:main`, `quest:side`
- **Priority:** `P0-blocker`
- **Klasifikasi Project Plan:** Wajib (Kolaborasi Git/GitHub, Secrets Hygiene, Uji Kelayakan Layanan M1) & Tambahan (CI/CD Otomatis)
- **Milestone:** `M1: Rancangan Disepakati (21–27 Nov 2026)`
- **Penanggung Jawab (Project Plan):** Zaki Eka Saputra, Mohamad Dwi Rezky Desyafa
- **Target Path:** `.github/workflows`, `.github/`, `scripts/`

### Context

Pengembangan monorepo lintas 3 learning path (Full-Stack, Data Science, AI Engineering) membutuhkan tata kelola Git/PR yang disiplin, pipeline GitHub Actions CI otomatis, perlindungan secrets agar tidak ada API key/password/data pribadi pelanggan yang bocor, serta pencatatan hasil uji kelayakan layanan (Modal GPU, API LLM, WAHA, deployment free tier) pada Minggu 1 (M1) sesuai jadwal Project Plan A26-CS105.

### Scope

**Requirement Wajib (Project Plan):**

- Penyiapan repositori GitHub dengan alur Pull Request terstandarisasi, default branch `dev` selama masa pengembangan aktif, template PR (`.github/pull_request_template.md`), dan aturan proteksi branch (ruleset).
- **Kepatuhan Visibilitas Repositori & Secrets Hygiene:** Project Plan menetapkan repositori **wajib private**, tanpa password, token, API key, data gaji, maupun data pribadi nyata pelanggan (`data/raw/*`, `.env`, `apps/web/.env` wajib diabaikan `.gitignore`). _(Catatan Audit: repositori saat ini terdeteksi berstatus `PUBLIC` — lihat bagian Keputusan Konfirmasi di bawah)._
- Pipeline GitHub Actions CI (`.github/workflows/ci.yml`) yang berjalan otomatis pada `push` dan `pull_request` ke `dev` serta mendukung pemicu manual `workflow_dispatch`:
  - Node.js/TypeScript: `npm run format:check`, `npm run lint`, `npm run db:validate`, `npm run db:generate`, `npm run typecheck`, `npm run build`, `npm run smoke`, dan `npm run test:coverage`.
  - Python (`apps/ai-service`): `ruff format --check`, `ruff check`, `mypy`, dan `pytest --cov`.
  - Validasi Docker Compose (`compose.dev.yaml` & `compose.vps.yaml`) dan build image VPS tanpa deploy.
- Pencatatan hasil **uji kelayakan layanan M1** (akun/kredit Modal GPU, API LLM, WAHA, dan platform deployment free tier).

**Rekomendasi Teknis / Implementasi:**

- Tambahkan pemindaian rahasia otomatis (_secrets scanning_ / skrip deteksi pola `.env` & token) pada pipeline CI atau pre-commit lokal.
- Aktifkan aturan _auto-close issue_ via `Closes #<nomor>` pada default branch `dev` beserta sinkronisasi status kartu GitHub Project Board.

**Out-of-Scope:**

- Continuous Deployment (CD) otomatis langsung ke VPS produksi dari runner publik tanpa persetujuan (deployment VPS terkontrol dilakukan pada `OPS-02`).

### Business Rules

- Dilarang keras meng-commit `.env`, password, API key LLM, token Modal/WAHA, `DATABASE_URL` produksi, data gaji, atau PII nyata pelanggan.
- Seluruh integrasi kode ke `dev` wajib melalui Pull Request dengan seluruh check CI berstatus hijau (lulus).
- _Feature freeze_ ditetapkan pada **akhir Minggu 3 (11 Des 2026)**; setelah itu hanya PR perbaikan bug dan dokumentasi yang diizinkan.

### API Contract

Tidak berlaku (tugas non-API). Mengonfigurasi tata kelola repositori, GitHub Actions CI, dan keamanan secrets.

### Acceptance Criteria

- [ ] `.github/workflows/ci.yml` aktif untuk `push`/`pull_request` ke `dev` dan `workflow_dispatch`, serta terverifikasi lulus (hijau) pada PR nyata.
- [ ] Seluruh gerbang kualitas (Prettier, ESLint, Prisma validate/generate, TypeScript typecheck, Vitest, Ruff, Mypy, Pytest, dan validasi Docker Compose) berjalan deterministik di CI.
- [ ] Template PR (`.github/pull_request_template.md`) aktif beserta checklist guardrail proyek.
- [ ] Aturan proteksi branch (`dev` & `main`) aktif dan `.gitignore` memblokir `.env`, `apps/web/.env`, serta `data/raw/*`.
- [ ] Catatan hasil uji kelayakan layanan M1 (Modal GPU, API LLM, WAHA, deployment free tier) terdokumentasi.

### Keputusan yang Membutuhkan Konfirmasi (PIC / Tim)

- `[Perlu Konfirmasi Tim & PIC]` **Penyelarasan Visibilitas Repositori:** Project Plan secara eksplisit menyatakan _"Repository wajib private"_, namun repositori `Catering-Si-Kembar/smart-catering` saat ini berstatus **`PUBLIC`**. Tim perlu segera mengubah repositori menjadi `PRIVATE` (dengan memperhatikan kuota menit GitHub Actions untuk private repo) atau mencatat keputusan resmi bila memang dibuka publik tanpa data UMKM nyata.
- `[Perlu Konfirmasi Tim]` Kesepakatan kebijakan _bypass_ admin vs kewajiban minimal 1 _peer review approval_ pada ruleset branch `dev` dan `main`.

### DoD

- [ ] Pipeline CI hijau pada branch `dev` dan terbukti berjalan otomatis pada pembukaan PR.
- [ ] Keputusan visibilitas repositori & secrets hygiene diverifikasi bebas kebocoran kredensial.
- [ ] Catatan uji kelayakan layanan M1 selesai ditulis.

### Dependencies

- **Prasyarat:** Struktur starter monorepo (`package.json`, `turbo.json`, `apps/ai-service/pyproject.toml`).
- **Terkait:** Pintu gerbang kualitas bagi seluruh issue (`FS-*`, `DS-*`, `AI-*`, `OPS-*`).

---

## [OPS-02] Docker Compose Produksi & Provisioning VPS + Reverse Proxy HTTPS

- **Labels:** `area:devops`, `priority:P1-mvp`, `quest:main`, `quest:side`
- **Priority:** `P1-mvp`
- **Klasifikasi Project Plan:** Wajib (Fondasi Aplikasi: Akses Publik & Persistensi Data) & Tambahan (Deployment VPS Terpisah: Express, FastAPI, PostgreSQL, ChromaDB, Worker, WAHA)
- **Milestone:** `M2: Fitur Inti Tersedia (28 Nov–4 Des 2026)` _(uji kelayakan VPS/Docker dimulai M1)_
- **Penanggung Jawab (Project Plan):** Mohamad Dwi Rezky Desyafa, Zaki Eka Saputra
- **Target Path:** `infra/docker`

### Context

Sesuai arsitektur Project Plan A26-CS105, frontend Next.js di-deploy terpisah di Vercel (`OPS-03`), sedangkan seluruh layanan backend dan pendukung—**Express REST `/api/v1` (`apps/api`), FastAPI (`apps/ai-service`), PostgreSQL, ChromaDB, Node.js worker (`apps/worker`), serta container WAHA**—dijalankan secara terisolasi pada VPS menggunakan Docker Compose (`infra/docker/compose.vps.yaml`) di balik Reverse Proxy HTTPS. Worker dijalankan bersama layanan backend pada VPS dan dipicu cron sistem VPS (**tanpa Redis/BullMQ**), dengan opsi pemicuan manual melalui backend bila cron gagal.

### Scope

**Requirement Wajib (Project Plan):**

- Penyempurnaan Dockerfile produksi (`api.Dockerfile`, `ai-service.Dockerfile`, `worker.Dockerfile`) dan orkestrasi `infra/docker/compose.vps.yaml` pada network internal terisolasi dengan volume persisten untuk PostgreSQL, ChromaDB, dan sesi WAHA.
- Konfigurasi Reverse Proxy HTTPS (Caddy atau Nginx + TLS Let's Encrypt) pada port `80`/`443` yang hanya mengekspos endpoint publik Express `/api/v1/*` secara aman.
- **Isolasi jaringan ketat:** port PostgreSQL (`:5432`), ChromaDB (`:8000`), FastAPI (`:8001`), Worker (`:3002`), dan WAHA **tidak dibuka ke IP publik internet**.
- Verifikasi persistensi data saat layanan/container dimulai ulang dan kesiapan koneksi HTTPS bagi frontend Vercel (`OPS-03`).
- Pengelolaan seluruh kredensial & API key hanya melalui environment variable server (`.env` di VPS, tidak di-commit ke Git).

**Rekomendasi Teknis / Implementasi:**

- Pasang `healthcheck` (`interval`, `timeout`, `retries`) dan kebijakan `restart: unless-stopped` pada seluruh service Compose.
- Sertakan extras Python (`uv sync --extra ml --extra rag`) pada build `ai-service.Dockerfile` sesuai modul yang diaktifkan.

**Out-of-Scope:**

- Hosting frontend Next.js di VPS (di-deploy di Vercel pada `OPS-03`).
- Orkestrasi Kubernetes / Docker Swarm atau penambahan Redis/BullMQ pada MVP.

### Business Rules

- Database PostgreSQL, ChromaDB, dan FastAPI dilarang keras diekspos langsung ke internet publik.
- Seluruh API key (LLM, Modal, WAHA, SMTP) dan kredensial DB hanya disimpan di environment variable server VPS.
- Data transaksi harus tetap utuh setelah restart container/layanan.

### API Contract

Tidak berlaku (tugas infrastruktur non-API). Mengekspos reverse proxy HTTPS publik yang meneruskan rute `/api/v1/*` ke Express backend (`:3001`).

### Acceptance Criteria

- [ ] `docker compose --env-file .env.example -f infra/docker/compose.vps.yaml --profile waha config --quiet` valid tanpa error.
- [ ] Seluruh kontainer (`postgres`, `chroma`, `api`, `ai-service`, `worker`, `waha`) berjalan dalam status `healthy` di VPS.
- [ ] Reverse proxy HTTPS merespons permintaan `/api/v1/health` dengan sertifikat TLS valid.
- [ ] Uji mulai ulang layanan (_container restart_) membuktikan data PostgreSQL dan koleksi vektor ChromaDB tetap persisten.
- [ ] Port internal PostgreSQL, ChromaDB, FastAPI, dan Worker terverifikasi tertutup dari akses luar publik.

### Keputusan yang Membutuhkan Konfirmasi (PIC / Tim)

- `[Perlu Konfirmasi Tim]` Spesifikasi VPS (min. 2 vCPU, 4 GB RAM, 40 GB SSD), penyedia VPS, dan domain/subdomain resmi (misal `api.<domain>`) untuk sertifikat HTTPS otomatis.
- `[Perlu Konfirmasi Tim]` Kebijakan pengaktifan profil WAHA (`--profile waha`) dan konfigurasi batas memori container agar VPS tetap stabil.

### DoD

- [ ] Seluruh berkas Dockerfile, `compose.vps.yaml`, dan konfigurasi reverse proxy tersimpan rapi di `infra/docker/`.
- [ ] Provisioning VPS berhasil diverifikasi dengan healthcheck dan uji restart.
- [ ] Panduan operasional deployment VPS terdokumentasi di README / `docs/`.

### Dependencies

- **Prasyarat:** `FS-02` (Skema Prisma), `FS-03` (Express API), `AI-01` (FastAPI), `OPS-01` (Secrets Hygiene).
- **Terkait:** Fondasi runtime VPS bagi `OPS-03` (Koneksi Vercel), `AI-04`/`AI-07`, `FS-09`, dan `OPS-05` (Cron & Failover).

---

## [OPS-03] Deployment Frontend Vercel & Verifikasi Koneksi BFF Desktop/Mobile

- **Labels:** `area:devops`, `priority:P1-mvp`, `quest:main`, `quest:side`
- **Priority:** `P1-mvp`
- **Klasifikasi Project Plan:** Wajib (Akses Publik Desktop & Ponsel, Penanganan Error) & Tambahan (Side Quest Full-Stack: Deployment Terpisah Free Tier di Vercel + Dokumentasi Build & URL Publik)
- **Milestone:** `M2: Fitur Inti Tersedia (28 Nov–4 Des 2026)`
- **Penanggung Jawab (Project Plan):** Zaki Eka Saputra, Haidar Habibi Al Farisi
- **Target Path:** `apps/web`, `README.md`

### Context

Sesuai Project Plan A26-CS105, frontend Next.js (`apps/web`) di-deploy terpisah pada free tier **Vercel**, berkomunikasi melalui **Axios** ke backend Express REST `/api/v1` yang berjalan di VPS (`OPS-02`), dan harus dapat diakses publik dari desktop maupun ponsel tanpa instalasi lokal. Sesuai Rencana Pengujian Project Plan, deployment juga wajib diuji saat layanan dimulai ulang dan saat koneksi database dimatikan agar aplikasi menampilkan pesan error yang jelas tanpa crash.

### Scope

**Requirement Wajib (Project Plan):**

- Konfigurasi proyek monorepo di Vercel (Root Directory `apps/web`, build command monorepo, dan variabel lingkungan produksi termasuk `API_BASE_URL` menuju URL HTTPS publik Express VPS).
- Konfigurasi CORS di backend Express agar mengizinkan domain produksi/preview Vercel secara aman.
- Verifikasi akses publik URL Vercel pada peramban desktop (`1440x900`) dan ponsel nyata (`390x844`).
- **Pengujian ketahanan sesuai Rencana Pengujian Project Plan:**
  1. Buka URL publik di desktop dan ponsel → aplikasi dapat diakses dan data tampil benar.
  2. Mulai ulang layanan backend/DB → data tetap ada setelah layanan hidup kembali.
  3. Matikan koneksi database → aplikasi menampilkan pesan error jelas dan **tidak crash**.
- Dokumentasi hasil build dan tautan akses publik pada **README**.

**Rekomendasi Teknis / Implementasi:**

- Pertahankan pola BFF (`apps/web/app/api/*` → `API_BASE_URL`) sehingga seluruh panggilan browser melalui HTTPS domain yang sama dan secret server tidak pernah masuk bundle client (`NEXT_PUBLIC_*`).
- Pastikan header keamanan dasar (CSP, `X-Content-Type-Options`, `X-Frame-Options`) aktif.

**Out-of-Scope:**

- Custom domain berbayar (cukup domain `*.vercel.app` free tier; alternatif Netlify/Cloudflare Pages bila terjadi kendala kuota).
- Aplikasi mobile native Android/iOS.

### Business Rules

- Aplikasi wajib dapat dibuka langsung melalui URL publik HTTPS pada desktop dan ponsel.
- Dilarang menaruh kredensial/API key rahasia pada variabel berprefiks `NEXT_PUBLIC_`.
- Dilarang memanggil IP/port mentah VPS tanpa HTTPS dari browser.

### API Contract

Tidak berlaku (tugas deployment non-API). Menghasilkan URL publik HTTPS Vercel aktif yang terhubung ke Express `/api/v1`.

### Acceptance Criteria

- [ ] Build & deployment otomatis Vercel berhasil untuk monorepo `apps/web` tanpa error.
- [ ] URL publik Vercel dapat dibuka di desktop (`1440x900`) dan ponsel (`390x844`) dengan navigasi responsif tanpa _horizontal overflow_.
- [ ] Komunikasi Axios frontend/BFF menuju Express REST `/api/v1` di VPS berjalan lancar tanpa error CORS.
- [ ] Uji mulai ulang layanan membuktikan data tetap tersimpan; uji mematikan koneksi database menampilkan pesan error yang jelas di UI tanpa crash.
- [ ] Hasil build dan tautan URL publik terdokumentasi di README proyek.

### Keputusan yang Membutuhkan Konfirmasi (PIC / Tim)

- `[Perlu Konfirmasi Tim]` Penentuan akun Vercel tim, nama proyek Vercel, dan branch pemicu deployment otomatis (`dev` untuk staging/demo vs `main` untuk rilis final).
- `[Perlu Konfirmasi Tim]` Daftar origin CORS domain preview Vercel pada konfigurasi Express backend.

### DoD

- [ ] Aplikasi web aktif di URL publik Vercel dan terhubung end-to-end dengan backend Express VPS.
- [ ] Hasil uji desktop, ponsel, restart layanan, dan simulasi DB mati tercatat di Spreadsheet uji.
- [ ] Tautan publik dan catatan build masuk ke README.

### Dependencies

- **Prasyarat:** `FS-01` (App Shell Web), `OPS-02` (Reverse Proxy HTTPS Express VPS).
- **Terkait:** Platform demonstrasi publik untuk uji pengguna & skenario 100 nasi box pada `FS-09`.

---

## [OPS-04] Deployment SLM/LLM Open-Source di Modal GPU (vLLM)

- **Labels:** `area:devops`, `priority:P2-side-quest`, `quest:side`
- **Priority:** `P2-side-quest` _(fitur tambahan — tidak boleh menunda alur utama)_
- **Klasifikasi Project Plan:** Tambahan (Side Quest Gen AI: Hosting Mandiri SLM/LLM Open-Source via Modal GPU & vLLM untuk AI Business Insight)
- **Milestone:** `M2: Fitur Inti Tersedia (28 Nov–4 Des 2026)` _(selaras jadwal Project Plan: uji kelayakan Modal GPU di M1, penyiapan inference Modal GPU di M2 agar `AI-06` siap diintegrasikan di M3)_
- **Penanggung Jawab (Project Plan):** Adnan Mufti Maulana, Mohamad Dwi Rezky Desyafa
- **Target Path:** `infra/modal`

### Context

Sesuai Project Plan A26-CS105, fitur nilai tambah **AI Business Insight (`AI-06`)** memanfaatkan **SLM/LLM open-source** yang di-host mandiri menggunakan **Modal Serverless GPU dan vLLM**, disiapkan terpisah dari layanan chatbot RAG (yang tetap memakai API LLM proprietary). Jadwal Project Plan menempatkan uji awal Modal GPU pada M1 dan **penyiapan inference Modal GPU pada M2** sehingga modul `AI-06` siap diintegrasikan bersama Dasbor Analitik (`FS-08`) pada M3 sebelum feature freeze.

### Scope

**Requirement Wajib (Project Plan untuk Infrastruktur Modal GPU):**

- Skrip deployment serverless GPU di `infra/modal/serve_vllm.py` menyajikan endpoint OpenAI-compatible (`/v1/chat/completions` dan `/health`) menggunakan engine vLLM.
- Pengunduhan bobot model open-source efisien (misal Qwen2.5-7B-Instruct atau Llama-3.2-3B, atau model lebih kecil/terkuantisasi sebagai opsi cadangan hemat kredit) ke Modal Volume cache untuk mempercepat cold start.
- Pengamanan endpoint menggunakan `Authorization: Bearer <MODAL_AUTH_TOKEN>` dari Modal Secrets / environment variable (tidak pernah di-commit ke Git).
- Pengaturan auto-scale ke 0 (`container_idle_timeout`) serta pemantauan pemakaian kredit komputasi, _cold start_, dan latensi inferensi.
- Pengujian akses endpoint dari `apps/ai-service` dan dokumentasi langkah deployment & pemantauan kredit di `infra/modal/README.md`.

**Rekomendasi Teknis / Implementasi:**

- Gunakan GPU hemat biaya (NVIDIA T4 16GB atau L4/A10G) dengan `container_idle_timeout=60` detik agar kredit gratis Modal tidak habis saat idle.
- Catat waktu _cold start_ dan _warm latency_ pada README sebagai bahan evaluasi `AI-06`.

**Out-of-Scope:**

- Fine-tuning bobot LLM (menggunakan model instruct open-source siap pakai).
- Menggunakan endpoint SLM Modal ini untuk menggantikan API LLM pada chatbot RAG (`AI-05`).
- Hosting GPU fisik _on-premise_.

### Business Rules

- Endpoint inferensi GPU dilarang terbuka publik tanpa autentikasi Bearer Token.
- Wajib menerapkan _scale-to-zero_ saat idle untuk melindungi kredit komputasi.
- Seluruh token/secret Modal dikelola via Modal Secrets dan environment server, dilarang masuk Git.

### API Contract

#### Daftar Endpoint Eksternal (OpenAI-Compatible vLLM)

| Method | Path                                                            | Fungsi                                                       | Autentikasi / Role                         |
| :----- | :-------------------------------------------------------------- | :----------------------------------------------------------- | :----------------------------------------- |
| `POST` | `https://<workspace>--vllm-serve.modal.run/v1/chat/completions` | Inferensi chat completions SLM/LLM open-source untuk `AI-06` | `Authorization: Bearer <MODAL_AUTH_TOKEN>` |
| `GET`  | `https://<workspace>--vllm-serve.modal.run/health`              | Pemeriksaan kesehatan runtime vLLM                           | `Authorization: Bearer <MODAL_AUTH_TOKEN>` |

_(Catatan: Endpoint eksternal vLLM mengikuti format standar OpenAI-compatible dan tidak menyajikan Scalar `/docs` internal monorepo)._

### Acceptance Criteria

- [ ] Skrip `infra/modal/serve_vllm.py` tervalidasi dan berhasil di-deploy ke Modal pada M2.
- [ ] Endpoint vLLM merespons permintaan chat completion OpenAI-compatible dengan autentikasi Bearer Token valid dan menolak permintaan tanpa token valid (`401 Unauthorized`).
- [ ] Kontainer terbukti melakukan _scale-down_ ke 0 GPU saat idle melewati batas timeout.
- [ ] Pemanggilan live dari `apps/ai-service` berhasil; waktu _cold start_, _warm latency_, dan estimasi konsumsi kredit dicatat di dokumentasi.
- [ ] Tersedia rencana cadangan model lebih kecil/terkuantisasi jika latensi terlalu tinggi atau kredit menipis.

### Keputusan yang Membutuhkan Konfirmasi (PIC / Tim)

- `[Perlu Konfirmasi Tim]` Akun Modal GPU dan ketersediaan kredit komputasi tim.
- `[Perlu Konfirmasi Tim]` Pemilihan bobot model final (misal Qwen2.5-7B-Instruct vs Llama-3.2-3B atau versi terkuantisasi AWQ/FP8) berdasarkan hasil uji latensi & kualitas narasi Bahasa Indonesia.

### DoD

- [ ] Skrip deployment dan panduan pemantauan kredit tersimpan di `infra/modal/`.
- [ ] Endpoint aktif teruji dari `apps/ai-service` siap digunakan oleh `AI-06` di M3.
- [ ] Tidak ada token Modal yang terekspos di repositori.

### Dependencies

- **Prasyarat:** `OPS-01` (Secrets Hygiene & uji kelayakan akun Modal M1).
- **Terkait:** Prasyarat langsung bagi modul AI Business Insight `AI-06` (M3).

---

## [OPS-05] Penjadwalan Cron Worker VPS, Backup DB/Chroma & Uji Failover Pra-Demo

- **Labels:** `area:devops`, `priority:P2-side-quest`, `quest:side`
- **Priority:** `P2-side-quest` _(infrastruktur pendukung reliabilitas & cron reminder)_
- **Klasifikasi Project Plan:** Tambahan (Penjadwalan Cron Sistem VPS + Worker Node.js Tanpa Duplikasi, Pemulihan & Uji Ketahanan Pra-Demo)
- **Milestone:** `M4: Validasi & Finalisasi (12–20 Des 2026)` — **PENTING (Kepatuhan Feature Freeze):** Konfigurasi cron sistem VPS untuk memicu worker Node.js wajib selesai paling lambat **akhir M3 (11 Des 2026)** bersama `FS-09`; fase **M4 (12–20 Des 2026)** difokuskan khusus pada pengujian cron ganda tanpa duplikasi, verifikasi retry & manual fallback, backup/restore, serta uji failover pra-demo 100 nasi box.
- **Penanggung Jawab (Project Plan):** Mohamad Dwi Rezky Desyafa, Zaki Eka Saputra
- **Target Path:** `apps/worker`, `infra/docker`, `scripts/`

### Context

Sesuai Project Plan A26-CS105, reminder otomatis dijalankan oleh **worker Node.js (`apps/worker`) yang dipicu cron sistem pada VPS** (tanpa Redis/BullMQ), dilengkapi pencatatan status pengiriman agar tidak terjadi duplikasi serta rencana cadangan berupa **pemicuan manual melalui backend jika cron gagal** dan menjalankan ulang reminder yang gagal berdasarkan log tanpa mengulangi pengiriman yang sudah berhasil. Menjelang demonstrasi skenario 100 nasi box pada M4, tim DevOps juga memastikan kesiapan backup/restore PostgreSQL & ChromaDB serta lulus uji ketahanan (_failover_) pra-demo.

### Scope

**Requirement Wajib (Project Plan — Cron selesai ≤ akhir M3; Pengujian Menyeluruh di M4):**

- Konfigurasi cron sistem pada VPS Ubuntu untuk memicu eksekusi `apps/worker` secara berkala (memanggil `POST /api/v1/reminders/process-due` dengan `X-Internal-Token` — tanpa Redis/BullMQ).
- Verifikasi rencana cadangan bila cron gagal: pemicuan ulang reminder gagal berdasarkan log secara manual melalui endpoint backend (`ADMIN`) tanpa mengulangi reminder yang sudah berstatus `DELIVERED`/`SENT`.
- **Pengujian Menyeluruh Pra-Demo (M4):**
  1. **Uji Cron Ganda (Anti-Duplikasi):** Menjalankan cron VPS **dua kali** untuk jadwal reminder yang sama (pesanan H-1 & pembayaran belum lunas) → memastikan 0 notifikasi duplikat terkirim.
  2. **Uji Kegagalan Kanal:** Mematikan salah satu kanal (misal WAHA) → kegagalan tercatat di log dan berhasil dicoba ulang saat kanal pulih.
  3. **Uji Reboot & Restart Layanan:** Simulasi restart seluruh container/VPS → memastikan `postgres`, `chroma`, `api`, `ai-service`, `worker` kembali `healthy` dan seluruh data transaksi + vektor tetap utuh.
  4. **Uji Koneksi DB Terputus:** Mematikan sementara `postgres` → aplikasi menampilkan pesan error jelas dan tidak crash permanen saat DB pulih.

**Rekomendasi Teknis / Implementasi:**

- Skrip backup harian terkompresi untuk PostgreSQL (`scripts/backup-db.sh` dengan `pg_dump` non-locking, format `backup_smartcatering_YYYYMMDD_HHMMSS.sql.gz`, retensi >= 7 hari) dan arsip volume ChromaDB (`scripts/backup-chroma.sh`) beserta uji restorasi.
- Endpoint liveness internal worker `:3002/health` untuk healthcheck Docker Compose (dikecualikan dari envelope `{ data, meta }` dan Scalar `/docs` sesuai ADR-0004 karena `apps/worker` adalah background daemon independen).

**Out-of-Scope:**

- Menambahkan Redis/BullMQ atau message broker terpisah pada fase MVP.
- Replikasi database multi-region atau langganan cloud storage backup berbayar.

### Business Rules

- Eksekusi cron berulang pada jadwal yang sama **dilarang keras** menghasilkan pengiriman notifikasi ganda.
- Pemrosesan ulang reminder yang gagal hanya boleh menargetkan catatan `FAILED` di `NotificationLog`, tidak mengulangi yang sudah terkirim.
- `apps/worker` tetap independen dari internal source code `apps/api` maupun `apps/ai-service` (komunikasi hanya melalui HTTP internal terautentikasi `X-Internal-Token`).
- Backup database tidak boleh mengunci transaksi operasional yang sedang berjalan.

### API Contract

#### Endpoint Liveness Internal Worker (Pengecualian ADR-0004)

| Method | Path      | Fungsi                                                                      | Autentikasi / Role                  |
| :----- | :-------- | :-------------------------------------------------------------------------- | :---------------------------------- |
| `GET`  | `/health` | Liveness & uptime internal daemon worker (`:3002`) untuk Docker healthcheck | Internal Docker Network VPS `:3002` |

### Acceptance Criteria

- [ ] Cron sistem VPS terkonfigurasi aktif (selesai ≤ akhir M3) dan memicu worker pengingat sesuai jadwal tanpa Redis/BullMQ.
- [ ] Uji menjalankan cron VPS **dua kali** pada jadwal reminder yang sama membuktikan **0 pengiriman duplikat**.
- [ ] Uji mematikan satu kanal dan menjalankan ulang (otomatis atau manual fallback via backend) membuktikan item gagal tercatat dan terkirim ulang tanpa mengulang item yang sudah sukses.
- [ ] Skrip backup `backup-db.sh` dan `backup-chroma.sh` berhasil membuat arsip bertanda waktu ISO dan lulus **uji restorasi (_restore test_)**.
- [ ] Simulasi restart/reboot layanan membuktikan seluruh container (`postgres`, `chroma`, `api`, `ai-service`, `worker`) pulih otomatis dalam kondisi `healthy` dan data tetap utuh.
- [ ] Daftar ceklis failover pra-demo selesai diisi dan dicatat di Spreadsheet uji & dokumentasi infrastruktur.

### Keputusan yang Membutuhkan Konfirmasi (PIC / Tim)

- `[Perlu Konfirmasi Tim]` Penetapan interval crontab VPS (misal tiap 15 menit atau jam tertentu), direktori backup lokal VPS (misal `/var/backups/smart-catering`), dan jadwal jam backup harian (misal 02.00 WIB).

### DoD

- [ ] Konfigurasi cron VPS dan skrip backup/restore tersimpan rapi di `infra/` & `scripts/`.
- [ ] Seluruh skenario uji anti-duplikasi, retry, backup/restore, dan failover pra-demo lulus dan terdokumentasi.
- [ ] Prosedur pemulihan manual jika cron gagal tercatat di dokumentasi operasional.

### Dependencies

- **Prasyarat:** `OPS-02` (Docker Compose VPS), `FS-09` (Endpoint & Worker Reminder), `AI-07` (Integrasi Kanal WAHA).
- **Terkait:** Menjamin stabilitas sistem selama demonstrasi akhir skenario 100 nasi box pada M4.
