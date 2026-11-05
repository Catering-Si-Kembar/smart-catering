# ADR-0003: PostgreSQL Relasional via Prisma Lazy dan Chroma Terpisah Milik AI Service

**Tanggal:** 2026-11-04 · **Status:** accepted · **Diperbarui:** 2026-11-05

**Pengambil keputusan:** pemilik proyek; diperbarui untuk mencerminkan perpindahan kepemilikan boundary Chroma ke `apps/ai-service`.

## Konteks

Scope terbaru memisahkan data relasional transaksional dan penyimpanan vector. Fase 0 belum memiliki model bisnis, collection, embedding, atau retrieval; infrastruktur tidak boleh diklaim sebagai fitur RAG aktif. Selain itu, dengan hadirnya layanan Python `@smart-catering/ai-service`, boundary akses Chroma perlu ditempatkan pada layanan yang benar-benar akan menjalankan pipeline RAG.

## Keputusan

1. **PostgreSQL & Prisma Lazy (`packages/db` → `apps/api`)**:
   - Gunakan image PostgreSQL biasa tanpa extension pgvector, dengan satu owner Prisma di `packages/db`.
   - Schema Prisma Fase 0 tidak memiliki model bisnis. `getDb()` memvalidasi `DATABASE_URL` saat pemakaian nyata, membuat satu client lazy per proses, dan tidak membuka koneksi pada import/build maupun saat melayani `/health`, `/docs`, atau `/api/openapi`.
   - Pada Compose VPS, `VPS_DATABASE_URL` diteruskan hanya menjadi runtime `DATABASE_URL` milik service `api`.
2. **Chroma Terpisah Milik `@smart-catering/ai-service`**:
   - Gunakan Chroma sebagai service vector terpisah yang tetap internal pada VPS (`http://chroma:8000`).
   - Kepemilikan boundary Chroma dan variabel `CHROMA_URL` kini berada di **`apps/ai-service`** (`apps/ai-service/app/chroma/README.md`), bukan lagi di `apps/api`.
   - Pada Fase 0, `GET /health` pada `ai-service` adalah liveness proses murni dan tidak membuka koneksi ke Chroma. Client `chromadb==1.5.9` dideklarasikan pada optional extra `rag` di `apps/ai-service/pyproject.toml` untuk fase implementasi RAG mendatang.

## Alternatif yang dipertimbangkan

- **PostgreSQL + pgvector:** satu datastore, tetapi bertentangan dengan keputusan arsitektur memakai Chroma terpisah.
- **Menyimpan `CHROMA_URL` di kedua `apps/api` dan `apps/ai-service`:** melanggar prinsip single ownership; `apps/api` cukup mengenal `AI_SERVICE_URL`, sedangkan `apps/ai-service` mengenal `CHROMA_URL`.

## Konsekuensi

**Positif:** owner data relasional (`packages/db` / `apps/api`) dan owner data vector (`apps/ai-service`) terpisah bersih; health/build tidak memerlukan DB atau Chroma online.

**Biaya:** operator mengelola dua datastore (`postgres` dan `chroma`) beserta backup/restore named volumes masing-masing.

## Rujukan

[Environment](../environment.md) · [Arsitektur](../architecture.md) · [VPS](../deployment-vps.md) · [Indeks ADR](README.md)
