## Ringkasan Perubahan

<!-- Jelaskan secara singkat apa yang diubah dan mengapa perubahan ini dibutuhkan. -->

-

## Issue Terkait

<!-- Ganti nomor di bawah agar issue tertutup otomatis saat PR di-merge ke branch default (contoh: Closes #3). Hapus atau tambahkan baris sesuai kebutuhan. -->

Closes #<nomor-issue>

## Area & Jenis Perubahan

- [ ] `area:fullstack` (`apps/web`, `apps/api`, `packages/db`)
- [ ] `area:ds` (`data/`, `notebooks/`, forecasting)
- [ ] `area:ai` (`apps/ai-service`, ChromaDB, RAG, SLM)
- [ ] `area:devops` (`infra/`, `.github/`, deployment, worker)
- [ ] Fitur baru / Bugfix / Dokumentasi / Refactor

## Checklist Verifikasi Lokal

- [ ] `npm run format:check` lulus
- [ ] `npm run lint` lulus (ESLint + Ruff)
- [ ] `npm run typecheck` lulus (TypeScript + Mypy)
- [ ] `npm test` lulus (Vitest + Pytest)
- [ ] `npm run build` lulus
- [ ] Jika menyentuh endpoint API: kontrak OpenAPI 3.1.0 & Scalar di `/docs` sudah diperiksa

## Checklist Guardrail Proyek

- [ ] Tidak ada file `.env`, password, API key, token, atau data mentah UMKM (`data/raw/*`) yang ikut ter-commit
- [ ] Tidak ada data pribadi nyata (PII) pelanggan/UMKM di kode, screenshot, maupun contoh payload
- [ ] Tidak ada tombol mati atau halaman "segera hadir" pada alur utama
- [ ] Data sintetis (jika ada) bertanda `is_synthetic = true` dan sumber data/model terdokumentasi
- [ ] Boundary monorepo terjaga (`apps/web` tidak mengakses DB/`apps/ai-service` langsung; `apps/worker` independen dari internal `apps/api`/`apps/ai-service`)

## Bukti Uji / Tangkapan Layar

<!-- Sertakan tangkapan layar mobile (390px) & desktop (1440px) bila mengubah UI, atau ringkasan metrik/log bila mengubah API, model AI, atau DS. -->
