# Modul `chroma` (`apps/ai-service/app/chroma`)

Batas modul untuk adaptor dan manajemen koleksi vector database Chroma yang diakses oleh layanan Python AI (`@smart-catering/ai-service`) melalui variabel lingkungan `CHROMA_URL`.

## Batas Jaringan & Kepemilikan

- Kepemilikan integrasi Chroma berada sepenuhnya di `apps/ai-service` (bukan di `apps/api` atau `apps/worker`).
- Pada pengembangan lokal, `CHROMA_URL` mengarah ke `http://127.0.0.1:8000`; pada topologi Docker Compose VPS mengarah ke DNS internal `http://chroma:8000`.

**Status Fase 0:** Hanya dokumentasi batas arsitektur. `GET /health` merupakan pemeriksaan liveness murni dan tidak membuka koneksi ke Chroma pada Fase 0.
