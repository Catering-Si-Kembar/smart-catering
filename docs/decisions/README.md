# Architecture Decision Records

**Diperbarui:** 2026-11-23

ADR berikut mencatat keputusan arsitektur Fase 0 yang telah diterima pengguna, termasuk perluasan ke enam workspace dengan layanan Python/FastAPI AI (`uv`) dan standar kontrak REST/OpenAPI 3.1. Tidak ada file ADR lama pada audit awal; keputusan lama hanya disebut dalam rencana yang kini [diganti](../superpowers/plans/2026-11-04-fase-0-setup-monorepo.md). Karena itu tidak dibuat file historis palsu seolah pernah diimplementasikan.

| ADR                                | Keputusan                                                                                                   | Status   | Tanggal    |
| ---------------------------------- | ----------------------------------------------------------------------------------------------------------- | -------- | ---------- |
| [0001](0001-hybrid-deployment.md)  | Web Vercel; API, AI service Python/FastAPI, worker, dan infra di VPS; gerbang keamanan docs produksi        | accepted | 2026-11-05 |
| [0002](0002-minimal-workspaces.md) | Enam workspace (`web`, `api`, `ai-service`, `worker`, `db`, `types`), kontrak REST/OpenAPI 3.1              | accepted | 2026-11-05 |
| [0003](0003-postgres-chroma.md)    | PostgreSQL via Prisma lazy milik API/db; Chroma terpisah milik `ai-service`                                 | accepted | 2026-11-05 |
| [0004](0004-independent-worker.md) | Worker mandiri always-on dengan liveness internal mentah tanpa ketergantungan API/AI/docs                   | accepted | 2026-11-05 |
| [0005](0005-express-joi-api-v1.md) | Migrasi backend API ke Express 5.3.0 + Joi 18.3.2 + rute `/api/v1`, penataan modul bisnis & ruang kerja tim | accepted | 2026-11-23 |

Keputusan ini mengganti asumsi **dua Vercel, worker lokal saja, pgvector, dan sebelas workspace/shared-RAG/ML packages**, serta memigrasikan backend operasional ke **Express 5.3.0 + Joi 18.3.2** dengan rute `/api/v1`. Boundary bisnis transaksional (`auth`, `menus`, `orders`, `finance`, `analytics`, `chat`, `reminders`) dan integrasi (`waha`, `email`) berada di `apps/api` (`apps/api/src/`), sedangkan boundary `rag`, `insight`, `ml/{relevance,forecasting,sentiment}`, dan `chroma` berada di `apps/ai-service` (Python 3.12 + `uv`). Kedua backend REST (`api` dan `ai-service`) mematuhi kontrak envelope `{ data, meta }`, RFC 9457 Problem Details, `X-Request-Id`, paginasi reusable, serta OpenAPI 3.1.0 + Scalar (`@scalar/api-reference@1.76.4`). Ruang kerja tim ditata melalui `data/`, `notebooks/`, `infra/modal/`, dan `docs/spec/`. Status accepted berarti pilihan desain diterima, **bukan** bukti deployment/checks telah lulus. Lihat [PRD v2.2](../PRD_FASE_0.md), [arsitektur](../architecture.md), dan [batas bukti](../README.md#status-dan-batas-bukti).
