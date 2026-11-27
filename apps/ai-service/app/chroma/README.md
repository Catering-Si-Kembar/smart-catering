# Modul `chroma` (`apps/ai-service/app/chroma`)

Modul integrasi vector database ChromaDB dan retrieval knowledge base terkurasi tervalidasi PIC untuk layanan AI Catering Si Kembar (`@smart-catering/ai-service`), memenuhi deliverable **`AI-04`** (Issue `#19`).

---

## 1. Arsitektur & Batas Jaringan

- **Kepemilikan:** Integrasi Chroma berada sepenuhnya di `apps/ai-service` (bukan di `apps/api` atau `apps/worker`).
- **Topologi Jaringan:**
  - Pengembangan lokal: `CHROMA_URL=http://127.0.0.1:8000`
  - Topologi Docker Compose VPS: `CHROMA_URL=http://chroma:8000`
  - Nama koleksi default: `CHROMA_COLLECTION_NAME=catering_knowledge`
- **Abstraksi Adapter (`VectorStoreAdapter`):**
  - `InMemoryVectorStoreAdapter`: Implementasi pure-Python deterministik berbasis `LocalHashEmbeddingFunction` untuk eksekusi CI minimal `--isolated` tanpa dependensi eksternal.
  - `ChromaHttpVectorStoreAdapter`: Adapter HTTP client resmi ChromaDB dengan lazy import (`importlib.import_module("chromadb")`) sehingga instalasi dasar base/CI tetap ringan dan bebas error.

---

## 2. Kurasi Dokumen Knowledge Base & 4 Metadata PIC

Seluruh dokumen pengetahuan disimpan di folder `data/knowledge/` dalam format Markdown ber-frontmatter YAML terstruktur:

| File                | Kategori  | Domain Pengetahuan                                                                        | Status Kurasi   |
| ------------------- | --------- | ----------------------------------------------------------------------------------------- | --------------- |
| `menus.md`          | `menu`    | Katalog Nasi Box, Nasi Liwet Tampah, Tumpeng Kuning, Snack Box, Prasmanan Silver & Gold   | Tervalidasi PIC |
| `faq.md`            | `faq`     | Minimal order (20 box / 50 prasmanan), lead time H-3/H-7, area Bandung Raya, halal/alergi | Tervalidasi PIC |
| `sop.md`            | `sop`     | SOP pencatatan order, persiapan dapur H-1, standar kebersihan food safety, pengantaran    | Tervalidasi PIC |
| `payment_policy.md` | `payment` | Uang muka DP minimal 60%, pelunasan H-1, kebijakan pembatalan/reschedule, invoice         | Tervalidasi PIC |

### 4 Metadata Wajib PIC

Setiap chunk dokumen menyertakan metadata:

1. `source`: Nama file sumber (mis. `menus.md`)
2. `validated_at`: Tanggal validasi PIC (mis. `2026-11-27`)
3. `version`: Versi rilis dokumen kurasi (mis. `1.0`)
4. `validation_status` / `is_verified`: Status validasi (`verified` / `true`). Dokumen `draft` / `is_verified: false` secara ketat disaring dan ditolak dari query produksi.

Bebas PII nyata (tanpa nama pelanggan/rekening pribadi asli) dan bebas HPP rahasia. Nilai bisnis yang memerlukan verifikasi berkala ditandai dengan `[Menunggu Konfirmasi PIC]`.

---

## 3. Strategi Chunking & Deterministic Embedding

- **Chunking:** Algoritma berbasis heading konteks (`##`) dan paragraf memecah dokumen menjadi potongan berukuran ideal 300–500 karakter (rentang ketat 80–650 karakter) dengan overlap 50 karakter untuk paragraf panjang.
- **Embedding Deterministik (`LocalHashEmbeddingFunction`):**
  - Menggunakan hashing `hashlib.blake2b` signed projections ke vektor berdimensi 384 dengan normalisasi L2.
  - Memanfaatkan ekspansi sinonim domain boga katering (`dp` <-> uang muka down payment, `katering` <-> catering, `ongkir` <-> pengantaran).
  - Cosine distance threshold anti-halusinasi: `max_distance = 0.65`. Pertanyaan di luar domain menghasilkan `total_hits: 0` (`results: []`).

---

## 4. Hasil Evaluasi Hit@3 & Negative Rejection

Evaluasi dijalankan menggunakan runner CLI deterministik:

```bash
uv run --project apps/ai-service --frozen --isolated python -m app.chroma.ingest --in-memory --eval
```

### Metrik Evaluasi Aktual

- **Total Positive Queries:** 16 (4 query per domain dokumen)
- **Hits @ 3:** 16 / 16
- **Hit Rate @ 3:** `1.0` (100.0%, target `>= 0.85`)
- **Metadata Complete Ratio:** `1.0` (100.0%, 4 field PIC lengkap pada seluruh chunk terambil)
- **Total Negative Queries:** 4 (di luar domain: kernel Linux, sushi Jepang, jadwal kereta api, kurs valuta)
- **Negative Rejected:** 4 / 4
- **Negative Rejection Rate:** `1.0` (100.0% penolakan sempurna, `results: []`)

---

## 5. Kontrak Endpoint REST API

1. `POST /api/v1/chroma/query`:
   - Header: `X-Internal-Token`
   - Body: `{"query": "Berapa ketentuan minimal DP pembayaran katering?", "top_k": 3, "category": "payment"}`
   - Respons 200: Daftar hit chunk terurut jarak kemiripan terdekat.
   - Respons Error RFC 9457: `401` (Unauthorized), `404` (Collection Not Found / belum ingest), `422` (Query kosong), `503` (ChromaDB service unavailable).

2. `POST /api/v1/chroma/ingest`:
   - Header: `X-Internal-Token`
   - Body: `{"knowledge_dir": null}`
   - Respons 200: Ringkasan idempoten ingest (`files_processed: 4`, `chunks_upserted: 20`, `total_chunks: 20`, `idempotent: true`).
   - Respons Error RFC 9457: `401` (Unauthorized), `422` (Path traversal `..` / direktori tidak valid), `503` (ChromaDB service unavailable).
