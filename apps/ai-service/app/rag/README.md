# Modul `rag` (`apps/ai-service/app/rag`)

Implementasi **Agentic RAG Dual-Source (`AI-05`)** untuk asisten operasional resmi **Catering Si Kembar** dengan arsitektur bersih (_Clean Architecture_), dependency injection, dan guardrails keamanan ketat.

## Arsitektur & Alur Pipeline (`LangGraph StateGraph`)

```text
Request (/api/v1/rag/chat)
  └─► 1. guardrail_check   ──► Blokir direct prompt injection, SQL bebas, & exfiltrasi rahasia (+ audit log JSON)
  └─► 2. relevance_gate    ──► Model relevansi 2 kelas AI-02 (relevant vs out_of_domain); tolak sopan tanpa LLM
  └─► 3. agent_reason      ──► Prompt terstruktur + few-shot (tanpa klasifikasi intent) + window chat history
  └─► 4. execute_tools     ──► Allowlist 4 read-only tools (maks 3 iterasi), sanitasi indirect injection
  └─► 5. finalize          ──► Grounding check (forbidden/not_found/anti-halusinasi) & graceful fallback
```

## Dua Sumber Utama Tool Calling (Tanpa SQL Bebas)

1. **Knowledge Base ChromaDB (`AI-04`)** — `search_catering_knowledge`:
   - Mengambil informasi **menu, FAQ, SOP operasional, dan aturan pembayaran** yang telah tervalidasi PIC (`is_verified = true`, `validation_status = "verified"`) beserta 4 metadata wajib (`source`, `validated_at`, `version`, `validation_status`).
2. **Database Operasional PostgreSQL melalui Backend Read-Only Tools Express (`FS-07`)** — hanya HTTP `GET` berparameter ketat ke `BACKEND_API_URL`:
   - `get_order_details` → `GET /api/v1/internal/agent-tools/orders`
   - `get_production_schedule` → `GET /api/v1/internal/agent-tools/schedule`
   - `get_invoice_and_payment_status` → `GET /api/v1/internal/agent-tools/invoices` _(penegakan RBAC oleh backend Express melalui `X-Internal-Token` + `X-Actor-Role` terverifikasi; peran `STAFF` ditolak `403` dan dicatat di log keamanan)_.

## Struktur Modul

- `schemas.py`: Domain model Pydantic strict (`RelevanceDecision`, `KnowledgeChunk`, `OperationalToolResult`, `LLMResponse`, `AgentContext`, `RetrievalEvalSample`, `RetrievalEvalReport`).
- `ports.py`: Protocol/Interface (_Dependency Inversion_) untuk classifier `AI-02`, ChromaDB `AI-04`, Express read-only backend `FS-07`, dan API LLM.
- `guardrails.py`: Deteksi _prompt injection_, _SQL injection/SQL bebas_, eksfiltrasi kredensial, sanitasi _indirect injection_ + delimiter `<TOOL_OUTPUT>`, audit logger JSON (`smart_catering.ai_service.security`), dan `DomainRelevanceClassifier` (memuat artefak `AI-02` `joblib` bila ada dengan fallback deterministik).
- `prompts.py`: System prompt terstruktur, contoh _few-shot_ (tanpa klasifikasi intent), dan pesan respons standar.
- `tools.py`: `ToolRegistry` berbasis allowlist (4 read-only tools) mendukung OpenAI tool schema dan `langchain_core.tools.StructuredTool`.
- `adapters.py`: Adapter konkret `ChromaKnowledgeBaseAdapter`, `ExpressReadOnlyToolsAdapter` (HTTP `GET` only), dan `OpenAICompatibleLLMClient` (API LLM proprietary saja; tidak pernah mengalihkan RAG ke SLM Modal GPU).
- `graph.py`: Orkestrasi `AgenticRagGraph` berbasis `langgraph.graph.StateGraph` (saat extra `rag` terpasang) dengan fallback state-machine identik untuk lingkungan CI ringan tanpa extra.
- `service.py`: Facade `AgenticRagService`, factory `build_default_rag_service`, dan utilitas evaluasi `evaluate_retrieval_hit_at_3`.

## Dependensi & Variabel Lingkungan

- Optional extra `rag` (`pyproject.toml`): `chromadb==1.5.9`, `httpx==0.28.1`, `langchain==1.4.8`, `langgraph==1.2.19`.
- Konfigurasi env (`apps/ai-service/app/config.py`): `BACKEND_API_URL`, `CHROMA_URL`, `CHROMA_COLLECTION_NAME`, `RAG_TIMEOUT_SECONDS`, `INTERNAL_SERVICE_SECRET`, `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`.

## Hasil Evaluasi Otomatis (`AI-05`)

> **Catatan Transparansi:** Evaluasi berikut dijalankan pada suite otomatis `tests/test_agentic_rag.py` (dengan runtime live `langgraph==1.2.19` & `langchain-core==1.7.5`). Pengujian live penuh terhadap koleksi ChromaDB tervalidasi PIC, model `joblib` latih sendiri, dan endpoint Express read-only akan divalidasi ulang setelah `AI-02`, `AI-04`, dan `FS-07` selesai terintegrasi.

### 1. Evaluasi Retrieval `Hit@3` & Kelengkapan 4 Metadata PIC

| Domain Uji | Contoh Pertanyaan Uji              | Sumber Target       | Hasil `Hit@3` | 4 Metadata PIC (`source`, `validated_at`, `version`, `validation_status`) |
| :--------- | :--------------------------------- | :------------------ | :-----------: | :-----------------------------------------------------------------------: |
| Menu       | Harga paket nasi box ayam lengkuas | `menus.md`          |      Hit      |                           Lengkap (`verified`)                            |
| FAQ        | Minimal pemesanan nasi box         | `faq.md`            |      Hit      |                           Lengkap (`verified`)                            |
| SOP        | SOP dapur konfirmasi H-2           | `sop.md`            |      Hit      |                           Lengkap (`verified`)                            |
| Pembayaran | Aturan pembayaran uang muka DP 60% | `payment_policy.md` |      Hit      |                           Lengkap (`verified`)                            |

- **Ringkasan Otomatis:** `4/4` (`hit_rate_at_3 = 1.0`, `metadata_complete_ratio = 1.0`); dokumen berstatus `draft` / `is_verified = false` tersaring keluar secara ketat.

### 2. Daftar 10 Pertanyaan di Luar Konteks (_Out-of-Domain_)

Seluruh 10 skenario berikut diuji di `test_ten_out_of_domain_questions_rejected_politely_without_calling_llm` dan ditolak secara sopan (`is_relevant = false`, `tools_called = []`, **0 panggilan API LLM**):

| No  | Pertanyaan di Luar Konteks                                    | Kategori         |      Status Guardrail      |
| :-: | :------------------------------------------------------------ | :--------------- | :------------------------: |
|  1  | Tolong buatkan kode Python untuk sorting algoritma quicksort. | Pemrograman      | Ditolak sopan (0 LLM call) |
|  2  | Siapa presiden Indonesia yang menjabat pada pemilu terakhir?  | Politik          | Ditolak sopan (0 LLM call) |
|  3  | Berapakah hasil integral dari x pangkat dua terhadap dx?      | Matematika       | Ditolak sopan (0 LLM call) |
|  4  | Bagaimana prakiraan cuaca hujan di Bandung hari ini?          | Cuaca            | Ditolak sopan (0 LLM call) |
|  5  | Apakah harga saham dan bitcoin sedang naik minggu ini?        | Finansial/Kripto | Ditolak sopan (0 LLM call) |
|  6  | Berapa skor pertandingan sepak bola liga Inggris semalam?     | Olahraga         | Ditolak sopan (0 LLM call) |
|  7  | Buatkan puisi cinta tentang senja di pantai.                  | Sastra/Umum      | Ditolak sopan (0 LLM call) |
|  8  | Terjemahkan kalimat bahasa Inggris berikut ke bahasa Jepang.  | Terjemahan Umum  | Ditolak sopan (0 LLM call) |
|  9  | Jelaskan sejarah perang dunia kedua secara singkat.           | Sejarah          | Ditolak sopan (0 LLM call) |
| 10  | Bagaimana cara memperbaiki error komponen React TypeScript?   | Pemrograman      | Ditolak sopan (0 LLM call) |

### 3. Uji Keamanan Tools, Prompt Injection & Kegagalan Layanan

- **Anti-SQL Bebas & Allowlist Tool:** Upaya `SELECT * FROM ...`, `DROP TABLE ...`, dan pemanggilan tool tak terdaftar (`execute_raw_sql`) diblokir dan dicatat pada structured audit log `rag_security_event`.
- **Direct & Indirect Prompt Injection:** Permintaan pengabaian aturan/ekstraksi system prompt diblokir sebelum memanggil LLM; instruksi berbahaya dalam chunk dokumen dinetralkan dan dibungkus tag `<TOOL_OUTPUT>`.
- **RBAC Backend-Enforced:** Peran `STAFF` yang meminta invoice menerima penolakan sopan (`FORBIDDEN_DATA_REPLY`) ketika Express mengembalikan `403`, tanpa kebocoran nominal dan tercatat di log keamanan.
- **Kegagalan Layanan:** Timeout, HTTP `429` kuota habis, kredensial kosong, dan gangguan ChromaDB mengembalikan _graceful fallback_ (`is_fallback = true`) tanpa crash dan tanpa mengalihkan RAG ke Modal SLM.
