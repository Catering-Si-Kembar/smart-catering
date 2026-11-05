# Deployment Vercel — frontend saja

**Diperbarui:** 2026-11-05 · **Status:** panduan konfigurasi, bukan bukti deployment

## Batas deployment

Hanya **`apps/web`** menjadi project Vercel. `apps/api`, `apps/ai-service`, `apps/worker`, PostgreSQL, Chroma, dan WAHA **tidak dideploy ke Vercel**. Tidak ada project Vercel kedua untuk API maupun Python serverless function untuk AI service, tidak ada Vercel Cron, database managed yang diasumsikan, ataupun worker di function serverless. Seluruh layanan backend dan infra mengikuti [deployment VPS](deployment-vps.md).

Nama project, akun/team, repository remote, domain dan URL deployment belum ditetapkan oleh panduan ini. Gunakan resource sebenarnya yang disediakan pemilik; jangan menyalin domain contoh seolah telah aktif.

## Prasyarat

1. Repository Git yang benar telah tersedia pada provider yang didukung, dengan izin import project.
2. Pemeriksaan terpadu lokal/CI telah dijalankan dan output ditinjau. Panduan ini tidak menyatakan hasilnya.
3. Akses Vercel, kebijakan branch Preview/Production, dan kapasitas plan sudah dikonfirmasi operator.
4. Untuk komunikasi API pada fase berikutnya: API VPS memiliki URL HTTPS yang benar dan dapat diakses dari server Vercel. Alamat container/loopback VPS (`127.0.0.1:3001` atau `http://ai-service:8001`) tidak dapat dipakai dari Vercel.

## Pengaturan project monorepo

| Pengaturan                        | Nilai/prosedur                                                                            |
| --------------------------------- | ----------------------------------------------------------------------------------------- |
| Project                           | Satu project frontend dengan nama yang disetujui pemilik                                  |
| Framework Preset                  | Next.js                                                                                   |
| Root Directory                    | `apps/web`                                                                                |
| Akses file di luar Root Directory | Aktifkan penyertaan source di luar direktori agar root tooling/shared workspace tersedia  |
| Node.js Version                   | Jalur `24.x` yang tersedia pada Vercel; cocokkan kompatibilitas dengan Node 24.15.0 lokal |
| Package manager                   | npm sesuai `packageManager` root, `npm@12.1.0`; konfirmasi versi pada log install         |
| Install Command                   | `cd ../.. && npm ci`                                                                      |
| Build Command                     | `cd ../.. && npm run build -- --filter=@smart-catering/web...`                            |
| Output Directory                  | Default Next.js; jangan override ke `out` atau folder API                                 |
| Production Branch                 | Pilih branch yang benar sesuai kebijakan pemilik; tidak diasumsikan oleh dokumen          |

Command di atas mengasumsikan working directory command Vercel adalah `apps/web`, sesuai Root Directory. Ia kembali ke root repository agar satu `package-lock.json` dan graph Turbo dipakai. Filter `--filter=@smart-catering/web...` hanya membangun `@smart-catering/web` beserta dependency shared TypeScript yang dideklarasikan (`@smart-catering/types`); ia **tidak** membangun `apps/api`, `apps/worker`, ataupun `apps/ai-service`, sehingga build Vercel tidak membutuhkan Python atau `uv`.

Entry frontend adalah `apps/web/app/page.tsx` dengan layout/CSS pada `apps/web/app`, tanpa `src`. Install npm12 membaca `allowScripts` root, hanya mengizinkan `prisma@7.10.1`, `@prisma/engines@7.10.1`, dan `esbuild@0.28.2` secara exact; jangan menambahkan blanket approval pada konfigurasi provider.

## Environment Preview dan Production

| Variabel web           | Nilai                                                                        |
| ---------------------- | ---------------------------------------------------------------------------- |
| `NEXT_PUBLIC_APP_NAME` | `Smart Catering`; aman untuk browser                                         |
| `API_BASE_URL`         | URL HTTPS API VPS yang sebenarnya untuk environment terkait; **server-only** |

Fase 0 belum melakukan fetch API, sehingga landing page tidak membuktikan konektivitas VPS. Backend health berada di `GET /health` pada base URL API dengan kontrak respons `{"data":{"status":"ok","service":"api"},"meta":{"requestId":"<uuid>"}}` (`HealthResponse` dari `@smart-catering/types`). Ketika fetch ditambahkan, gunakan server component/server action/server-side handler melalui `API_BASE_URL`, lalu kirim data yang aman ke browser. Jangan membuat `NEXT_PUBLIC_API_BASE_URL` atau memberikan `DATABASE_URL`, `AI_SERVICE_URL`, `CHROMA_URL`, `WAHA_API_KEY`, maupun `DOCS_PASSWORD` ke frontend Vercel.

## Pelaksanaan dan bukti yang diperlukan

1. Import repository sebenarnya, pilih `apps/web`, set konfigurasi/versi/env di atas.
2. Jalankan deployment dengan izin pemilik dan tinjau log install/scoped build.
3. Buka URL yang **benar-benar dihasilkan Vercel**, periksa HTTP, identitas Smart Catering, stylesheet, dan error browser.
4. Simpan URL deployment, commit, status build, dan hasil pemeriksaan aktual. Jangan menambahkan badge hijau sebelum hasil tersedia.
5. Pada fitur API mendatang, uji HTTPS server Vercel→API VPS secara terpisah; landing statis tidak cukup.

Dokumentasi ini tidak menjalankan langkah deployment dan tidak mengklaim DNS/TLS/CI remote telah teruji. Lihat [status bukti](README.md#status-dan-batas-bukti).

## Referensi resmi

- [Vercel — monorepos](https://vercel.com/docs/monorepos)
- [Vercel — configuring a build](https://vercel.com/docs/builds/configure-a-build)
- [Next.js — deployment output dan standalone](https://nextjs.org/docs/app/api-reference/config/next-config-js/output)

Konfigurasi standalone API dan image Python AI service adalah untuk VPS, bukan Vercel. Keputusan hybrid dijelaskan dalam [ADR 0001](decisions/0001-hybrid-deployment.md).
