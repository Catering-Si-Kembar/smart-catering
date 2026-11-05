# Dokumentasi Smart Catering

**Diperbarui:** 2026-11-05

Fondasi Fase 0 menggunakan **Hybrid Minimal Monorepo**: empat aplikasi dan dua shared packages sebagai enam workspace npm. Dependency Node dikunci dalam satu `package-lock.json` root; dependency Python dikunci dalam `apps/ai-service/uv.lock`. Frontend ditujukan ke Vercel; API, AI service, worker, dan infrastruktur internal ditujukan ke VPS.

## Urutan baca

| Dokumen                                                                       | Kegunaan                                                                    |
| ----------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| [README root](../README.md)                                                   | Quick start, command utama, kontrak API, dan CI                             |
| [PRD Fase 0 v2.2](PRD_FASE_0.md)                                              | Scope, kebutuhan teknis, dan acceptance criteria                            |
| [Struktur repository](repository-structure.md)                                | Pemilik source, entry point, dan artefak generated                          |
| [Development](development.md)                                                 | Install npm + uv, menjalankan aplikasi, dan troubleshooting                 |
| [Environment](environment.md)                                                 | Dua sumber env (`.env` root + `apps/web/.env`), allowlist, dan gerbang docs |
| [Arsitektur](architecture.md)                                                 | Boundary aplikasi, dependency, dan kontrak wire REST                        |
| [Diagram arsitektur](architecture.md#diagram-arsitektur)                      | Infografik kondisi Fase 0; tersedia dalam PNG dan SVG                       |
| [Deployment Vercel](deployment-vercel.md)                                     | Deployment frontend saja                                                    |
| [Deployment VPS](deployment-vps.md)                                           | API, AI service, worker, PostgreSQL, Chroma, dan WAHA opsional              |
| [ADR](decisions/README.md)                                                    | Keputusan arsitektur dan alternatif yang ditolak                            |
| [Rencana implementasi](superpowers/plans/2026-11-04-fase-0-setup-monorepo.md) | Urutan implementasi dan verifikasi clean checkout                           |
| [Changelog](../CHANGELOG.md)                                                  | Riwayat perubahan fondasi                                                   |

## Kepemilikan dan struktur

- `apps/web/app/`: Next.js frontend, tanpa lapisan `src` tambahan.
- `apps/api/app/` dan `apps/api/lib/`: Next.js backend, health, kontrak REST, Scalar/OpenAPI, serta boundary modul bisnis dan integrasi WAHA.
- `apps/ai-service/app/`: FastAPI dengan layout Python flat; pemilik boundary RAG, ML, dan Chroma. Ekstra RAG/ML dikunci tetapi tidak di-install secara default.
- `apps/worker/src/`: proses Node independen; tidak mengimpor internal API, mengakses database, atau menjalankan job bisnis pada Fase 0.
- `packages/db/src/` dan `packages/types/src/`: Prisma server-only dan tipe TypeScript bersama.

README pada boundary modul menjelaskan tanggung jawabnya, bukan implementasi fitur. Tidak ada `.gitkeep`; Git melacak file, bukan direktori kosong. `.gitignore` hanya mengecualikan artefak lokal/generated dan tidak mempertahankan folder kosong.

Audit awal hanya menemukan rencana implementasi, bukan source pnpm yang perlu dimigrasikan. [PRD v2.2](PRD_FASE_0.md) menormalisasi keputusan terbaru pengguna; bukan salinan verbatim PRD eksternal yang tidak tersedia sebagai source repository.

## Status dan batas bukti

Validasi lokal dijalankan pada Windows x64, Node `24.15.0`, npm `12.1.0`, uv `0.13.7`, dan Python `3.12.13` terkelola uv. Image Python VPS dipin terpisah ke `3.12.16-slim-bookworm` beserta digest-nya.

| Pemeriksaan              | Hasil yang diamati                                                                                                                                                                                     |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Install Node dan Python  | `npm install`, `npm ci`, dan sinkronisasi uv frozen berhasil; ekstra RAG/ML tidak diaktifkan                                                                                                           |
| Format dan lint          | Prettier, ESLint, Ruff format/check lulus                                                                                                                                                              |
| Typecheck                | TypeScript strict dan Mypy lulus                                                                                                                                                                       |
| Prisma                   | Client generation dan schema validation berhasil tanpa database online                                                                                                                                 |
| Test Node                | 133/133 lulus; statements 93.71%, branches 83.41%, functions 100%, lines 93.80%                                                                                                                        |
| Test Python              | 80/80 lulus; total coverage statement + branch 92.38%                                                                                                                                                  |
| Build                    | Enam task build dipaksa tanpa cache berhasil, termasuk kedua Next.js app dan distribusi Python                                                                                                         |
| Smoke produksi lokal     | Web, API, AI service, dan worker berjalan; health, UUID, HEAD, error 404/405, docs default tertutup, serta Basic Auth HTML/skema diuji                                                                 |
| Startup dua sumber env   | `dev:all`, empat `dev:*` individual, `dev:backend`, `start:all`, `start:backend`, serta empat `start:*` individual menjawab HTTP 200; port/flag root terbaca dan frontend tidak menerima nilai backend |
| Scalar melalui browser   | Kedua UI mengirim `/health` nyata dengan respons 200; request ke CDN tidak membawa Authorization; tidak ada error browser                                                                              |
| Web desktop/mobile       | Tampilan 1440px dan 390px diperiksa; mobile tanpa overflow horizontal, skip link keyboard memindahkan fokus ke main                                                                                    |
| Validitas OpenAPI        | Kedua dokumen lolos validator independen OpenAPI 3.1                                                                                                                                                   |
| Compose development/VPS  | Model konfigurasi valid dengan validator standalone Compose 5.7.0, termasuk profil WAHA                                                                                                                |
| Dependency produksi Node | `npm audit --omit=dev` melaporkan 0 vulnerability                                                                                                                                                      |
| Link dokumentasi         | 116 referensi relatif termasuk gambar, navigasi HTML, dan anchor pada 26 file Markdown valid                                                                                                           |

Coverage Node berlaku pada scope `vitest.config.ts` (helper kontrak API, validasi environment worker, serta `scripts/service-environment.mjs`), bukan klaim coverage seluruh UI/repository. Coverage Python berlaku pada `apps/ai-service/app`. Kedua suite menerapkan batas minimum 80% sesuai konfigurasinya.

### Batas lingkungan dan deployment

- Docker Engine dan instalasi Docker CLI standar tidak tersedia di host ini. Validasi model Compose **bukan** bukti image berhasil dibangun, container berjalan, query PostgreSQL berhasil, Chroma/WAHA sehat, atau volume persisten. Build image tersedia sebagai langkah CI untuk runner ber-Docker.
- Repository resmi [Catering-Si-Kembar/smart-catering-](https://github.com/Catering-Si-Kembar/smart-catering-) berstatus **private**. Jalur publikasi memakai `main` dan `dev`; hanya push `dev` dan pull request bertarget `dev` yang memicu workflow. Keberadaan Git/remote atau keberhasilan push tidak membuktikan CI, branch protection, maupun deployment Vercel/VPS telah lulus.
- TLS, DNS, backup, koneksi database, Chroma, dan pengiriman WhatsApp nyata belum diuji. Endpoint health hanya **liveness proses**, bukan readiness dependency.
- Dokumentasi produksi default nonaktif. Jika diaktifkan, HTML **dan** skema memerlukan HTTP Basic; pengaktifan wajib berada di belakang TLS. Kredensial tidak dimasukkan ke HTML atau URL. Scalar memerlukan akses browser ke bundle jsDelivr yang dipin; skema mentah tidak memerlukan CDN.
- Kontrak RFC 9457 berlaku pada request yang mencapai handler aplikasi. Metode transport seperti `TRACE` dapat ditolak framework sebelum handler; batasi metode di reverse proxy sesuai [batas HTTP sebelum handler aplikasi](deployment-vps.md#batas-http-sebelum-handler-aplikasi).
- ESLint tetap dipin pada major 9 karena batas peer dependency konfigurasi Next yang digunakan. Peringatan EOL dependency tidak disembunyikan dengan pemaksaan peer dependency.

Belum ada autentikasi pengguna bisnis, CRUD, chatbot, pipeline RAG, embedding, training/inference ML, reminder, atau pengiriman WhatsApp. Redis + BullMQ hanya didokumentasikan sebagai opsi masa depan; tidak di-install. Telegram tidak digunakan.
