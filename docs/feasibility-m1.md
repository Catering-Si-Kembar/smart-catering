# Catatan Tata Kelola Git/CI, Secrets Hygiene & Uji Kelayakan Layanan M1 (`OPS-01`)

**Diperbarui:** 2026-11-27 · **Milestone:** M1 (`21–27 Nov 2026`) · **Acuan:** Issue [#23](https://github.com/Catering-Si-Kembar/smart-catering/issues/23) & [Project Plan A26-CS105](Asah_2026_Project_Plan_A26-CS105.md)

Dokumen ini mencatat status tata kelola repositori GitHub, pipeline CI otomatis, perlindungan rahasia (_secrets hygiene_), serta hasil **uji kelayakan layanan M1** (Modal GPU, API LLM, WAHA, dan platform deployment free tier) secara objektif—membedakan hal yang sudah terverifikasi di kode/CI dengan item yang masih menunggu akun atau konfirmasi tim/PIC.

---

## 1. Tata Kelola Git/PR, Ruleset & GitHub Actions CI

| Komponen                       | Konfigurasi Aktif                                                                                                | Status Verifikasi                                                                                 |
| :----------------------------- | :--------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------ |
| **Default Branch Aktif**       | `dev` (branch rilis: `main`)                                                                                     | **Aktif** — seluruh PR fitur ditargetkan ke `dev`.                                                |
| **Template Pull Request**      | [`.github/pull_request_template.md`](../.github/pull_request_template.md)                                        | **Aktif** — memuat checklist verifikasi lokal, guardrail proyek, dan `Closes #<N>` / `Refs #<N>`. |
| **Branch Protection Ruleset**  | `Protect Main Branch` (`~DEFAULT_BRANCH` & `refs/heads/main`, minimal 1 approval)                                | **Aktif** — admin memiliki _bypass_ terkontrol; kebijakan final _bypass_ dicatat pada §4.         |
| **Auto-Close & Project Board** | `Closes #N` menutup issue saat merge ke default branch `dev`; gunakan `Refs #N` jika AC live belum selesai       | **Terverifikasi** — berjalan pada PR `#29` (`Closes #16`), `#33`–`#35` (`Refs #20/#21/#26`).      |
| **GitHub Actions CI**          | [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) (`push`/`pull_request` ke `dev` + `workflow_dispatch`) | **Terverifikasi Hijau** pada PR `#30`, `#32`, `#33`, `#34`, `#35`, `#36`, `#37`.                  |
| **Feature Freeze**             | **Akhir Minggu 3 (11 Des 2026)**                                                                                 | **Disepakati** — setelah 11 Des hanya PR bugfix, uji E2E, dan dokumentasi.                        |

### Ringkasan Gerbang Mutu di CI (`unit-tests` & `quality`)

1. **Secrets Hygiene Guard (`npm run security:check`):** Menjalankan [`scripts/check-secrets-hygiene.mjs`](../scripts/check-secrets-hygiene.mjs) untuk memastikan:
   - `.gitignore` melindungi `.env`, `.env.*`, `!.env.example`, `data/raw/*`, `!data/raw/README.md`, `*.pkl`, dan `*.joblib`.
   - Tidak ada file `.env` nyata, data mentah UMKM (`data/raw/*`), file private key (`*.pem`/`*.key`), atau biner ML (`*.joblib`/`*.pkl`) yang ikut ter-track di Git.
   - Seluruh variabel rahasia pada `.env.example` kosong.
   - Tidak ada pola token provider (GitHub, Google/Gemini, OpenAI/Anthropic, AWS, Modal, Private Key header) di berkas source yang ter-commit—tanpa pernah mencetak isi token ke log CI.
2. **Code Quality & Static Analysis:** Prettier (`format:check`), ESLint (`lint`), Prisma `db:validate` & `db:generate`, TypeScript `typecheck`, Ruff (`format` + `check`), Mypy `--strict` (`apps/ai-service` dan `infra/modal`), `npm run build -- --force`, dan `npm run smoke`.
3. **Automated Tests & Coverage (`>= 80%`):** Vitest (`--coverage`, mencakup kontrak Express, environment worker, allowlist `service-environment.mjs`, dan `check-secrets-hygiene.mjs`), Pytest (`--cov=app --cov-fail-under=80`), serta Pytest `infra/modal/test_modal_infra.py`.
4. **Container & Compose Validation:** `docker compose ... config --quiet` untuk `compose.dev.yaml` dan `compose.vps.yaml` (termasuk profil `waha`) serta build image VPS (`api`, `ai-service`, `worker`) tanpa deploy.

---

## 2. Catatan Uji Kelayakan Layanan M1

| Layanan / Platform                                          | Target Penggunaan                                                                         | Status Kelayakan Teknis M1                                                                                                                                                                                                                                                                                                    | Kendala / Batas Kuota                                                                                                                                        | Rencana Cadangan (Project Plan §4–§5)                                                                                                                                                          |
| :---------------------------------------------------------- | :---------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Modal Serverless GPU + vLLM (`OPS-04`, `AI-06`)**         | Serving SLM/LLM open-source (`Qwen2.5-7B-Instruct` / `3B`) khusus **AI Business Insight** | **Siap secara kode & arsitektur** — `infra/modal/` (auth proxy Bearer `401`, Volume cache, `scaledown_window=60`, profil `primary` L4 & `fallback`/`fallback_awq` T4) dan client `apps/ai-service/app/insight/` sudah ter-merge ke `dev` (PR `#34`, `#35`). **Akun & deploy live Modal tim:** `[Menunggu Aktivasi Akun Tim]`. | Kredit gratis ~$30/bln, cold start GPU, dan kompatibilitas kernel kuantisasi T4 (`awq`, bukan `awq_marlin`).                                                 | Profil `fallback` (`Qwen2.5-3B-Instruct` di `T4`) atau fallback naratif deterministik (`is_fallback=true`) agar PDF `FS-08` tetap berjalan; **tidak pernah** dipakai menggantikan RAG `AI-05`. |
| **Proprietary LLM API & Embedding (`AI-05`, `AI-04`)**      | Agentic RAG dual-source tool calling (`apps/ai-service/app/rag/`)                         | **Siap secara kode & arsitektur** — klien OpenAI-compatible + LangGraph + ChromaDB adapter + guardrails sudah ter-merge ke `dev` (PR `#33`). **API key provider final (Gemini vs OpenAI):** `[Menunggu Konfirmasi Tim]`.                                                                                                      | Rate limit / kuota gratis (`429`), timeout jaringan, dan biaya token.                                                                                        | Timeout + retry terbatas + pesan fallback jelas tanpa crash; opsi ganti provider OpenAI-compatible lain (Gemini/OpenAI/OpenRouter) melalui `LLM_BASE_URL` & `LLM_MODEL`.                       |
| **WhatsApp via WAHA (`AI-07`, `FS-09`)**                    | Kanal chatbot staf terdaftar (whitelist) & pengiriman reminder otomatis                   | **Konfigurasi container tervalidasi** — profil opt-in `waha` pada `compose.dev.yaml` & `compose.vps.yaml` lolos validasi Docker Compose di CI. **Pairing QR nomor cadangan:** `[Menunggu Konfirmasi PIC]`.                                                                                                                    | Bukan layanan resmi WhatsApp → risiko pembatasan akun; wajib memakai **nomor cadangan** (dilarang nomor utama UMKM) dengan volume rendah dan whitelist staf. | WhatsApp Cloud API (nomor uji) atau fallback kanal reminder in-app & email SMTP.                                                                                                               |
| **Deployment Free Tier (Vercel + VPS + Postgres + Chroma)** | Frontend Next.js di Vercel; Express API, FastAPI, Worker, Postgres 17, ChromaDB di VPS    | **Build & Compose tervalidasi CI** — `apps/web` (Next.js build), `apps/api`, `apps/ai-service`, `apps/worker`, dan build image VPS lulus CI. **Provisioning server/akun produksi:** `[Target M2: OPS-02 & OPS-03]`.                                                                                                           | Batas RAM/CPU VPS, kuota bandwidth Vercel free tier, konfigurasi TLS/HTTPS, dan isolasi port internal (`:8001`/`:3002` tidak publik).                        | Alternatif frontend (Netlify / Cloudflare Pages) dan alternatif hosting backend/Postgres bila kuota VPS terbatas.                                                                              |

---

## 3. Verifikasi Lokal Secrets Hygiene

Jalankan dari root repository sebelum membuka Pull Request:

```sh
npm run security:check
```

Aturan penting yang wajib dijaga seluruh anggota tim:

- **Dilarang keras** meng-commit `.env`, `apps/web/.env`, password DB, API key LLM, token Modal/WAHA, data gaji, maupun data pribadi nyata pelanggan (`data/raw/*`).
- Data sintetis untuk eksperimen/demo wajib disimpan di `data/synthetic/` dengan penanda eksplisit `is_synthetic = true`.

---

## 4. Keputusan Terbuka yang Membutuhkan Konfirmasi (PIC / Tim)

1. **`[Perlu Konfirmasi Tim & PIC]` Visibilitas Repositori (`PUBLIC` vs `PRIVATE`):**
   - Project Plan A26-CS105 (§4 & §5) menetapkan **"Repository wajib private"**.
   - Saat ini repositori `Catering-Si-Kembar/smart-catering` masih berstatus **`PUBLIC`** sementara untuk kelancaran kuota menit GitHub Actions (dengan jaminan 0 data UMKM nyata, 0 PII, dan 0 secret berkat `npm run security:check`). Tim perlu memutuskan jadwal peralihan ke `PRIVATE` atau mencatat persetujuan resmi PIC apabila tetap dibuka publik tanpa data mitra nyata.
2. **`[Perlu Konfirmasi Tim]` Kebijakan Ruleset `dev` & `main`:**
   - Menetapkan apakah admin tetap memiliki _bypass_ pada ruleset `Protect Main Branch` atau seluruh merge ke `dev` wajib melewati minimal 1 _peer review approval_ tanpa kecuali.
3. **`[Perlu Konfirmasi Tim]` Pemilihan Provider API LLM, Embedding & Akun Modal GPU:**
   - Menetapkan provider LLM (`Gemini` vs `OpenAI`), model embedding (`AI-04`), dan akun Modal GPU tim (`OPS-04`) pada awal M2 agar pengujian live dapat segera dijalankan.
