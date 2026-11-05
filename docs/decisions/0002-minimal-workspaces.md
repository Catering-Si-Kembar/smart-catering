# ADR-0002: Enam Workspace Hybrid, Layanan AI Python `uv`, dan Kontrak REST/OpenAPI 3.1

**Tanggal:** 2026-11-04 · **Status:** accepted · **Diperbarui:** 2026-11-05

**Pengambil keputusan:** pemilik proyek; pencatatan keputusan arsitektur enam workspace, kepemilikan AI, dan standar kontrak REST Fase 0.

## Konteks

Fondasi awal membatasi monorepo pada lima workspace Node.js sambil menyimpan folder placeholder `rag`, `ml`, dan `chroma` di dalam `apps/api`. Namun kebutuhan nyata pengembangan AI/RAG/ML berikutnya memerlukan ekosistem Python (FastAPI, Pydantic, LangChain, ChromaDB, scikit-learn) yang dikelola secara deterministik, sementara kedua backend HTTP (`apps/api` dan `apps/ai-service`) harus berbicara dengan kontrak REST, format error, korelasi request, paginasi, dan standar dokumentasi OpenAPI 3.1.0 yang seragam.

## Keputusan

1. **Enam Workspace Private (`0.0.0`)**:
   - Gunakan tepat enam workspace di bawah `apps/*` dan `packages/*`: `@smart-catering/web`, `@smart-catering/api`, `@smart-catering/ai-service`, `@smart-catering/worker`, `@smart-catering/db`, dan `@smart-catering/types`.
   - Pertahankan **satu `package-lock.json` di root** untuk seluruh ekosistem npm. `apps/ai-service/package.json` hanya berfungsi sebagai task wrapper npm/Turbo tanpa dependency Node.
   - Kelola ekosistem Python di `apps/ai-service` menggunakan **uv 0.13.7**, Python **3.12** (`>=3.12,<3.14`, `.python-version` `3.12`), `pyproject.toml`, dan **`apps/ai-service/uv.lock`**.
2. **Pemisahan Kepemilikan Bisnis vs AI (Tanpa Arsitektur Ganda)**:
   - `apps/api` memiliki modul bisnis transaksional (`apps/api/modules/{auth,orders,inventory,finance}`) dan integrasi WhatsApp (`apps/api/integrations/waha`).
   - `apps/ai-service` memiliki boundary `apps/ai-service/app/{rag,ml,chroma}`. Direktori placeholder lama `apps/api/modules/{rag,ml}` dan `apps/api/integrations/chroma` **dihapus** dari `apps/api`.
   - Dependency berat `rag` (`langchain==1.4.8`, `chromadb==1.5.9`) dan `ml` (`scikit-learn==1.9.1`) dideklarasikan sebagai `[project.optional-dependencies]` di `pyproject.toml` dan dikunci di `uv.lock`, tetapi tidak di-install pada `npm run ai:sync` maupun image Docker produksi Fase 0.
3. **Layout Source yang Ringkas**:
   - Next.js apps (`apps/web/app`, `apps/api/app` + `apps/api/lib`) dan Python FastAPI (`apps/ai-service/app` + `apps/ai-service/tests`) tidak memakai lapisan direktori `src`.
   - `apps/worker/src`, `packages/db/src`, dan `packages/types/src` tetap memakai `src` yang dikompilasi ke `dist`. Tidak ada `.gitkeep`.
4. **Kontrak Wire REST & OpenAPI 3.1.0 Bersama (`api` & `ai-service`)**:
   - Respons sukses `200`/`201`: `{"data": <payload>, "meta": {"requestId": "<uuid>"}}` (ditambah `meta.pagination` bila berpaginasi). Helper `204 No Content` mengembalikan body kosong tanpa JSON `Content-Type`.
   - Error standar **RFC 9457 `application/problem+json`** (`type`, `title`, `status`, `detail`, `instance` pathname saja, `requestId`, serta `errors: [{ path, code, message }]` pada `422 Unprocessable Content`). Error `500` selalu teredaksi (`"An unexpected error occurred."`).
   - Korelasi `X-Request-Id` menerima UUID RFC kanonis (v1–v8) lowercase atau membuat UUIDv4 baru.
   - Dokumentasi OpenAPI **3.1.0** (`/api/openapi` dan `/openapi.json` sebagai pengecualian protokol JSON mentah) dan UI Scalar (`/docs`, dipin ke `https://cdn.jsdelivr.net/npm/@scalar/api-reference@1.76.4` tanpa AI agent/telemetry/proxy/remote font).

## Alternatif yang dipertimbangkan

- **Menjalankan RAG/ML di dalam Node.js `apps/api`:** membatasi akses ke pustaka ML Python (`scikit-learn`) dan menyatukan beban CPU/memori AI dengan server transaksi; digantikan oleh `apps/ai-service`.
- **Mempertahankan folder `rag`/`ml`/`chroma` di `apps/api` sekaligus di `apps/ai-service`:** menciptakan kebingungan kepemilikan; folder lama di `apps/api` dihapus bersih.
- **Memasang seluruh paket LangChain/ChromaDB/scikit-learn pada install default Fase 0:** memperbesar image dan waktu install padahal belum ada pipeline aktif; dipilih pendekatan optional extras terkunci di `uv.lock`.

## Konsekuensi

**Positif:** batas kepemilikan Node API vs Python AI tegas, kontrak HTTP/error/OpenAPI 3.1 konsisten lintas bahasa, dan image produksi tetap ramping.

**Biaya:** pengembang dan CI menjalankan dua toolchain (`npm` + `uv`) yang diorkestrasi melalui script root dan Turborepo.

## Rujukan

[Struktur repository](../repository-structure.md) · [Development](../development.md) · [PRD v2.2](../PRD_FASE_0.md) · [Indeks ADR](README.md)
