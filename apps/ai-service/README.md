# Smart Catering AI Service

Layanan microservice kecerdasan buatan (_AI service_) untuk ekosistem **Catering Si Kembar**, dibangun menggunakan framework **FastAPI** berstandar Python asinkron modern pada port internal `:8001`. Layanan ini menyediakan klasifikasi relevansi domain, analisis sentimen umpan balik pelanggan, asisten percakapan operasional berbasis _Agentic RAG_, serta sintesis wawasan bisnis katering.

---

## 1. Rumusan Masalah & Arsitektur Solusi AI

### Konteks Mitra: Catering Si Kembar

Catering Si Kembar adalah penyedia jasa boga katering yang melayani pesanan prasmanan, nasi box, dan hidangan acara kantor serta keluarga. Seiring meningkatnya volume pesanan harian, operasional katering menghadapi kendala signifikan:

- **Pengguna Sasaran:** Pengelola/pemilik katering (`ADMIN`), staf operasional dapur dan pengantaran (`STAFF`), serta calon pemesan/pelanggan melalui kanal layanan yang terhubung lewat backend bisnis.
- **Penanganan Manual Terdahulu:**
  - Pencatatan pesanan bertumpu pada buku nota fisik dan berkas lembar sebar (Google Spreadsheet) yang dikelola terpisah-pisah.
  - Alur komunikasi pelanggan dan pengecekan ketersediaan menu mengandalkan daya ingat staf dapur, sehingga rentan memicu keterlambatan respons, miskomunikasi batas waktu pemesanan (_lead time_), serta kesalahan estimasi kapasitas porsi.
  - Ulasan pelanggan tidak terkonsolidasi secara terpusat, sehingga keluhan terkait cita rasa atau keterlambatan pengantaran lambat terdeteksi.

### Arsitektur Solusi AI

Untuk menyelesaikan masalah di atas, sistem Smart Catering mengintegrasikan layanan AI mandiri (`@smart-catering/ai-service`) yang dipanggil secara server-to-server oleh backend Express (`apps/api`) dengan arsitektur:

1. **API Serving Engine (FastAPI — `AI-01`):** Menyediakan REST API internal dengan dokumentasi otomatis **OpenAPI 3.1.0**, antarmuka **Scalar** (`/docs`, fail-closed di produksi), validasi skema ketat (_Pydantic strict_), serta pelacakan korelasi permintaan melalui `X-Request-Id`.
2. **Relevance Classifier (scikit-learn — `AI-02`):** Model klasifikasi 2 kelas (`relevant` vs `out_of_domain`) yang dilatih mandiri untuk menyaring pertanyaan luar konteks sebelum diteruskan ke pipeline generatif.
3. **Sentiment Analysis Engine (scikit-learn — `AI-03`):** Model klasifikasi sentimen ulasan pelanggan (`positive`/`negative`) untuk deteksi dini komplain dan agregasi dasbor analitik.
4. **Agentic RAG Assistant (ChromaDB + Proprietary LLM API — `AI-05`):** Pipeline _Retrieval-Augmented Generation_ berbasis dokumen SOP dan katalog katering tervalidasi PIC (`AI-04`) dengan _read-only tool calling_ dan guardrail anti-_prompt injection_.
5. **Business Insights Synthesizer (Modal Serverless GPU + vLLM — `AI-06`):** Model bahasa terbuka (_SLM/LLM open-source_) yang di-host mandiri di Modal GPU (`OPS-04`) untuk menyusun ringkasan eksekutif dan rekomendasi operasional dari metrik agregat dengan fallback deterministik.

---

## 2. Kontrak Endpoint & Standar Protokol

### Daftar Endpoint Aktif (`AI-01`)

| Method         | Path                                 | Tag         | Autentikasi             | Deskripsi                                       |
| -------------- | ------------------------------------ | ----------- | ----------------------- | ----------------------------------------------- |
| `GET` / `HEAD` | `/health`                            | `System`    | Publik (`security: []`) | Liveness probe layanan utama.                   |
| `GET` / `HEAD` | `/api/v1/health`                     | `System`    | Publik (`security: []`) | Alias liveness probe versi `/api/v1`.           |
| `GET` / `HEAD` | `/openapi.json`                      | `Docs`      | Gate `DOCS_ENABLED`     | Dokumen spesifikasi OpenAPI 3.1.0 resmi.        |
| `GET` / `HEAD` | `/docs`                              | `Docs`      | Gate `DOCS_ENABLED`     | UI interaktif Scalar API Reference.             |
| `POST`         | `/api/v1/ml/predict-relevance`       | `Relevance` | `X-Internal-Token`      | Klasifikasi relevansi 2 kelas domain katering.  |
| `GET`          | `/api/v1/ml/relevance/metadata`      | `Relevance` | `X-Internal-Token`      | Metadata versi dan metrik model relevansi.      |
| `POST`         | `/api/v1/ml/predict-sentiment`       | `Sentiment` | `X-Internal-Token`      | Klasifikasi sentimen ulasan tunggal.            |
| `POST`         | `/api/v1/ml/predict-sentiment/batch` | `Sentiment` | `X-Internal-Token`      | Klasifikasi sentimen ulasan secara batch.       |
| `POST`         | `/api/v1/rag/chat`                   | `RAG`       | `X-Internal-Token`      | Tanya-jawab SOP & operasional berbasis RAG.     |
| `POST`         | `/api/v1/insight/generate`           | `Insights`  | `X-Internal-Token`      | Sintesis laporan wawasan bisnis katering (SLM). |

> Endpoint retrieval ChromaDB (`/api/v1/chroma/*` — `AI-04`) dan inferensi forecasting (`/api/v1/ml/forecast/demand` — `DS-05`) ditambahkan pada modul `app/chroma/` dan `app/ml/forecasting/` pada tahap implementasi masing-masing.

### Standar Wire Contract

1. **Amplop Respons Berhasil (`200 OK`):**
   Setiap respons sukses membungkus payload pada kunci `data` dan metadata korelasi pada `meta`:

   ```json
   {
     "data": {
       "status": "ok",
       "service": "ai-service"
     },
     "meta": {
       "requestId": "01941234-5678-7abc-8def-0123456789ab"
     }
   }
   ```

2. **Format Standar Error (RFC 9457):**
   Seluruh kegagalan menghasilkan payload `Content-Type: application/problem+json` terstruktur tanpa membocorkan rincian internal atau secret:

   ```json
   {
     "type": "about:blank",
     "title": "Unprocessable Content",
     "status": 422,
     "detail": "Request validation failed.",
     "instance": "/api/v1/ml/predict-relevance",
     "requestId": "01941234-5678-7abc-8def-0123456789ab",
     "errors": [
       {
         "path": "text",
         "code": "invalid_value",
         "message": "Invalid value"
       }
     ]
   }
   ```

3. **Keamanan & Guardrail Autentikasi:**
   - **`X-Request-Id`:** Setiap permintaan menerima atau menghasilkan UUID kanonik versi 1–8 lowercase RFC untuk penelusuran terdistribusi.
   - **`X-Process-Time-Ms` & Structured Logging:** Setiap respons menyertakan header `X-Process-Time-Ms` yang mencatat durasi pemrosesan dalam milidetik, disertai pencatatan request log berformat JSON terstruktur (`event`, `method`, `path`, `status`, `durationMs`, `requestId`) tanpa merekam query string, kredensial autentikasi, atau secret.
   - **`X-Internal-Token`:** Endpoint internal `/api/v1/ml/*`, `/api/v1/rag/*`, dan `/api/v1/insight/*` diproteksi menggunakan pembandingan waktu konstan `hmac.compare_digest` terhadap `INTERNAL_SERVICE_SECRET`.
   - **Gerbang Dokumentasi (`DOCS_ENABLED`):** Di lingkungan produksi (`APP_ENV=production`), rute `/docs` dan `/openapi.json` dinonaktifkan secara _fail-closed_ kecuali jika `DOCS_ENABLED=true` dengan autentikasi HTTP Basic (`DocsBasicAuth`, `DOCS_PASSWORD` minimal 32 karakter di balik TLS).

---

## 3. Panduan Setup & Eksekusi Lokal

Layanan ini dikelola menggunakan manajer paket Python **`uv`** (`pyproject.toml` + `uv.lock`). Optional extras tersedia untuk tahap lanjutan: `ml` (`scikit-learn`, `pandas`, `joblib`), `rag` (`chromadb`, `langchain`, `langgraph`, `httpx`), dan `insight` (`httpx`).

### Sinkronisasi Dependency

Jalankan seluruh perintah berikut dari direktori `apps/ai-service/`:

```bash
uv sync --frozen
```

### Menjalankan Server Lokal

```bash
uv run --frozen uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

### Pemeriksaan Kualitas Kode & Tipe

```bash
# Format check
uv run --frozen ruff format --check app tests

# Linting check
uv run --frozen ruff check .

# Type checking ketat (Mypy strict)
uv run --frozen mypy app
```

### Eksekusi Unit Test & Ambang Coverage

```bash
uv run --frozen pytest --cov=app --cov-report=term-missing --cov-fail-under=80
```

### Evaluasi Model Relevansi 2 Kelas (AI-02)

Modul relevansi menyaring pertanyaan pelanggan ke dalam dua kelas: `relevant` (domain katering) dan `out_of_domain` (luar katering). Dataset awal dibangkitkan secara transparan berlabel `is_synthetic=true` pada `data/synthetic/relevance_dataset.csv` (439 sampel unik: 351 train / 88 test, rasio terstratifikasi 80:20 tanpa kebocoran data).

#### Tabel Perbandingan Model & Tuning

| Model Arsitektur                | Status Evaluasi                  | Holdout F1-score | Holdout Accuracy |
| ------------------------------- | -------------------------------- | ---------------- | ---------------- |
| `MultinomialNB (baseline)`      | Baseline tanpa tuning            | 0.8730           | 0.8182           |
| `LogisticRegression (baseline)` | Sebelum hyperparameter tuning    | 0.9402           | 0.9205           |
| `LogisticRegression (tuned)`    | Sesudah `GridSearchCV` 5-fold CV | 0.9735           | 0.9659           |

- **Hyperparameter Tuning:** Melalui 5-fold `StratifiedKFold` CV, parameter optimal diperoleh pada `C=10.0`, `class_weight='balanced'`, `ngram_range=(1, 1)`, dan `sublinear_tf=True`. F1-score meningkat dari `0.9402` menjadi `0.9735` dan akurasi meningkat dari `0.9205` menjadi `0.9659`.
- **Confusion Matrix Holdout:** `[[55, 0], [3, 30]]` (baris: ground truth `relevant` & `out_of_domain`; kolom: prediksi). Model mencapai presisi `0.9483` dan recall `1.0000` pada kelas relevan (0 false negative).
- **Alasan Pemilihan Model:** `LogisticRegression (tuned)` dipilih karena menghasilkan F1-score tertinggi (`0.9735`), probabilitas terkalibrasi, serta mendukung dual-artifact (bobot matematis JSON portable untuk CI minimal tanpa dependensi ML tambahan).
- **Rata-rata Latensi Inferensi:** `1.493 ms` per permintaan (jauh di bawah ambang SLA `< 100 ms`).
- **Rujukan Eksperimen:** Alur eksperimen mandiri dan evaluasi lengkap terdokumentasi pada notebook `notebooks/04_relevance_classification.ipynb`.

---

## 4. Kepatuhan & Guardrails Keamanan AI

1. **Pelatihan Model Mandiri:** Model klasifikasi relevansi (`AI-02`) dan sentimen (`AI-03`) dilatih mandiri menggunakan pustaka scikit-learn pada dataset terkurasi. Tidak menggunakan AutoML, model siap pakai TensorFlow Hub sebagai model utama, atau API LLM komersial sebagai pengganti model klasifikasi inti.
2. **Kepatuhan Privasi Data (Non-PII):** Data operasional riil pelanggan tidak disimpan pada repositori publik (`data/raw/*` diabaikan Git). Data sintetis wajib ditandai eksplisit dengan flag `is_synthetic`.
3. **Pemisahan Secret Ketat:** Kunci API LLM, secret token internal, dan kredensial Modal tidak pernah ditulis di kode sumber, log proses, atau respons error (`AppSettings` menyensor seluruh rahasia pada `__repr__`/`__str__`).
4. **Isolasi Kegagalan AI:** Kegagalan atau batas waktu (_timeout_) pada inferensi AI tidak boleh menghentikan fitur inti Smart Catering; respons error tertangani dengan kode RFC 9457 yang aman (`503 Service Unavailable` atau `504 Gateway Timeout`) serta fallback terkontrol.
