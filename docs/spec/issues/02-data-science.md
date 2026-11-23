# Spesifikasi Teknis: Data Science (`02-data-science.md`)

Berkas ini memuat spesifikasi teknis lengkap untuk 6 issue area Data Science (`DS-01` s.d. `DS-06`) mencakup pengumpulan dan anonimasi data katering, exploratory data analysis (EDA), penyusunan kamus data dan dataset sintetis, rekayasa fitur & modeling peramalan (_forecasting_), integrasi serving inferensi ke `apps/ai-service`, serta audit kualitas data akhir.

---

## [DS-01] Pengumpulan, Anonimasi & Data Wrangling Data UMKM

- **Labels:** `area:ds`, `priority:P0-blocker`, `quest:main`
- **Priority:** `P0-blocker`
- **Milestone:** `M1 (21–27 Nov 2026)`
- **Target Path:** `data/raw`, `notebooks`

### Context

Catering Si Kembar memiliki data operasional historis berupa rekap pemesanan di Google Spreadsheet, catatan nota fisik, serta daftar menu dan bahan baku. Namun, data mentah tersebut masih mengandung informasi pribadi pelanggan (PII seperti nomor telepon, nama lengkap pemesan, dan alamat rumah), format tanggal yang tidak seragam, nilai kosong (_missing values_), serta potensi duplikasi pencatatan. Tim Data Science perlu mengumpulkan, menganonimkan data sesuai standar etika dan privasi, serta melakukan pembersihan data (_data wrangling_) terstruktur agar siap dianalisis.

### Scope

**In-Scope:**

- Penarikan dan inventarisasi data mentah rekap transaksi katering ke folder lokal aman.
- Proses penyensoran dan anonimasi PII: menyamarkan nama pemesan (`Pelanggan_001`), menghapus alamat privat (hanya menyisakan cakupan wilayah kota/kecamatan), dan mengaburkan 4 digit terakhir nomor telepon.
- Penilaian kualitas data (_assessing data_): identifikasi missing values, data duplikat, format tanggal inkonsisten, dan outlier kuantitas pesanan.
- Pembersihan data (_cleaning data_): penanganan nilai kosong, standardisasi tipe data numerik dan datetime ISO 8601, pembuangan data duplikat, serta penyimpanan dataset bersih ke format CSV/Parquet standar.
- Notebook dokumentasi wrangling di `notebooks/01_data_wrangling.ipynb`.

**Out-of-Scope:**

- Menyimpan data mentah tanpa anonimasi ke dalam repositori git (aturan ketat: `data/raw/*` diabaikan oleh `.gitignore`).
- Menghapus transaksi anomali yang valid secara bisnis tanpa pencatatan alasan rasional.

### Business Rules

- Dilarang mempublikasikan atau meng-commit nama orang, nomor rekening bank, atau nomor kontak asli pelanggan UMKM ke repositori publik.
- Setiap pembersihan nilai kosong atau modifikasi format harus dicatat log perubahannya (_transformation log_).
- Transaksi bernilai porsi 0 atau bernilai negatif yang tidak memiliki keterangan pembatalan harus ditandai sebagai data rusak (_invalid record_).

### API Contract

Tidak berlaku (tugas non-API). Menghasilkan dataset terstruktur dan notebook pembersihan data di lingkungan Python.

### Acceptance Criteria

- [ ] Tersedia notebook `notebooks/01_data_wrangling.ipynb` yang dapat dijalankan dari atas ke bawah (_reproducible_) tanpa error.
- [ ] Seluruh data pelanggan berhasil dianonimkan (0 baris memuat nomor telepon asli atau nama lengkap riil).
- [ ] Format tanggal seluruh transaksi terstandardisasi menjadi `YYYY-MM-DD`.
- [ ] Tidak ada nilai hilang (_missing values_) pada kolom-kolom kritis: `order_date`, `menu_name`, `portions`, `total_price`.

### Technical Notes

- Ketersediaan izin ekspor Google Spreadsheet dari pemilik katering `[Menunggu Konfirmasi PIC]`.
- Penentuan batasan outlier pesanan ekstrim (misal: pesanan pesta > 1000 porsi) `[Perlu Konfirmasi Tim]`.

### DoD

- [ ] Dataset bersih tersimpan di direktori lokal dengan skrip pemrosesan terdokumentasi.
- [ ] Notebook wrangling memiliki teks markdown penjelasan yang sistematis.
- [ ] Tidak ada berkas rahasia data mentah yang bocor ke git status.

### Dependencies

- Prasyarat: Izin data dan ekspor file spreadsheet dari mitra UMKM.
- Terkait: Menjadi input wajib bagi `DS-02` (EDA) dan `DS-03` (Kamus Data).

---

## [DS-02] EDA 5 Pertanyaan Bisnis, Visualisasi & Rekomendasi Operasional

- **Labels:** `area:ds`, `priority:P1-mvp`, `quest:main`
- **Priority:** `P1-mvp`
- **Milestone:** `M2 (28 Nov–4 Des 2026)`
- **Target Path:** `notebooks`

### Context

Pengelola katering menghadapi kendala ketidakpastian dalam menentukan jumlah belanja bahan dan staf dapur pada hari-hari tertentu karena tidak memiliki visibilitas atas pola transaksi historis. Berdasarkan kesepakatan Project Plan, analisis data eksploratif (EDA) harus mampu menjawab 5 pertanyaan bisnis utama: (1) Menu apa yang paling sering dipesan (menu favorit)? (2) Berapa rata-rata jumlah porsi per pesanan? (3) Kapan waktu-waktu ramai pemesanan (hari dalam seminggu dan minggu dalam bulan)? (4) Bagaimana pola dan kepatuhan pembayaran pelanggan (pembayaran lunas vs piutang)? (5) Apa saja bahan baku utama yang paling banyak dikonsumsi?

### Scope

**In-Scope:**

- Analisis statistik deskriptif dan distribusi data transaksi bersih.
- Eksplorasi mendalam untuk menjawab kelima pertanyaan bisnis katering.
- Pembuatan visualisasi data yang informatif dan estetik (histogram, bar chart, line chart tren waktu, correlation matrix).
- Penyusunan ringkasan temuan (_key findings_) dan rekomendasi operasional praktis bagi efisiensi belanja dan jadwal kerja Catering Si Kembar.
- Notebook terstruktur di `notebooks/02_eda_business_questions.ipynb`.

**Out-of-Scope:**

- Pemodelan prediktif machine learning (dilakukan terpisah di `DS-04`).
- Visualisasi dashboard web dinamis (dilakukan di `FS-08`).

### Business Rules

- Analisis wajib mengaitkan temuan statistik dengan kondisi nyata operasional F&B katering.
- Dilarang memberikan rekomendasi bisnis yang tidak didasarkan pada bukti angka dan grafik pada analisis.
- Perhitungan menu terfavorit harus membedakan antara frekuensi pemesanan (_order count_) dan total akumulasi porsi yang diproduksi (_portion volume_).

### API Contract

Tidak berlaku (tugas non-API). Luaran berupa notebook analisis data dan visualisasi grafik statis.

### Acceptance Criteria

- [ ] Notebook `notebooks/02_eda_business_questions.ipynb` berhasil menjawab seluruh 5 pertanyaan bisnis secara komprehensif.
- [ ] Tersedia grafik visualisasi yang jelas dengan label sumbu, judul, dan legenda yang mudah dipahami.
- [ ] Terdapat bagian kesimpulan yang merinci rekomendasi operasional (misal: penyiapan bahan baku ayam pada hari Jumat-Minggu, rekomendasi batas minimum DP).
- [ ] Hasil analisis divalidasi dan dibandingkan dengan rekap aktual UMKM.

### Technical Notes

- Validasi temuan pola hari ramai dengan pengelola katering `[Menunggu Konfirmasi PIC]`.
- Sinkronisasi definisi metrik menu terlaris untuk dasbor web bersama tim Full-Stack `[Perlu Konfirmasi Tim]`.

### DoD

- [ ] Notebook EDA selesai dieksekusi, bersih, dan bebas dari error eksekusi cell.
- [ ] Ringkasan temuan 5 pertanyaan bisnis ditulis dalam format markdown siap pakai.
- [ ] File grafik penting diekspor untuk bahan presentasi dan laporan akhir.

### Dependencies

- Prasyarat: `DS-01` (Dataset Bersih Hasil Wrangling).
- Terkait: Menjadi dasar perancangan indikator KPI pada `FS-08` dan `DS-06`.

---

## [DS-03] Kamus Data, Generator Data Sintetik (`is_synthetic`) & Paket Dataset untuk Gen AI

- **Labels:** `area:ds`, `priority:P0-blocker`, `quest:main`, `quest:side`
- **Priority:** `P0-blocker`
- **Milestone:** `M1 (21–27 Nov 2026)`
- **Target Path:** `data/dictionary`, `data/synthetic`

### Context

Pengembangan model AI oleh tim AI Engineering (klasifikasi relevansi, analisis sentimen feedback pelanggan, dan retrieval RAG) sangat bergantung pada ketersediaan data teks yang representatif dan terstruktur. Namun, data riil dari UMKM pada awal proyek seringkali sangat terbatas jumlahnya atau tidak memiliki label sentimen dan teks pertanyaan pelanggan. Tim Data Science bertugas menyusun Kamus Data (_Data Dictionary_) resmi, membangun skrip generator data sintetis yang realistis dan berpenanda eksplisit `is_synthetic = true`, serta menyediakan paket data latih & uji yang terbagi bersih tanpa kebocoran data (_data leakage_).

### Scope

**In-Scope:**

- Penyusunan dokumen kamus data (`data/dictionary/data_dictionary.md`): nama kolom, tipe data, rentang nilai valid, dan deskripsi bisnis untuk setiap entitas data katering.
- Pembuatan generator data sintetis berbasis script Python (`data/synthetic/generate_synthetic_data.py`) untuk menghasilkan data pesanan simulasi, teks ulasan pelanggan, dan variasi pertanyaan seputar katering.
- Penandaan ketat kolom metadata `is_synthetic: boolean` pada seluruh baris data buatan.
- Pembagian partisi data latih dan uji (_train-test split_) kronologis/stratified yang mencegah kebocoran data untuk kebutuhan model AI.
- Penyediaan paket dataset siap latih (`train_relevance.csv`, `test_relevance.csv`, `train_sentiment.csv`, `test_sentiment.csv`).

**Out-of-Scope:**

- Menyamarkan data sintetis sebagai data transaksi asli UMKM tanpa penandaan (pelanggaran guardrail).
- Menggunakan generator pihak ketiga yang menghasilkan teks halusinasi di luar domain katering.

### Business Rules

- Seluruh baris data sintetis wajib memiliki nilai `is_synthetic = true` atau `1`.
- Distribusi kuantitas porsi dan harga pada data sintetis harus mengikuti rentang realistis yang diverifikasi dari data asli Catering Si Kembar.
- Data uji (_test set_) tidak boleh digunakan dalam tahap training maupun penyesuaian parameter generator.

### API Contract

Tidak berlaku (tugas non-API). Menghasilkan berkas kamus data markdown dan file dataset CSV/JSON di `data/`.

### Acceptance Criteria

- [ ] Berkas `data/dictionary/data_dictionary.md` memuat definisi lengkap seluruh atribut tabel katering.
- [ ] Skrip `generate_synthetic_data.py` dapat dijalankan dan menghasilkan dataset sintetis terdistribusi normal/wajar.
- [ ] 100% baris pada file data sintetis memiliki kolom `is_synthetic = true`.
- [ ] Paket dataset latih dan uji untuk AI Engineering tersedia dan lolos uji integritas skema data.

### Technical Notes

- Rasio proporsi pembagian data latih vs uji (misal 80:20) `[Perlu Konfirmasi Tim]`.
- Variasi gaya bahasa ulasan katering lokal (bahasa Indonesia informal / santai) `[Perlu Konfirmasi Tim]`.

### DoD

- [ ] Kamus data dan skrip generator tersimpan di direktori yang ditentukan.
- [ ] Paket dataset siap dikonsumsi oleh tim AI Engineering pada issue `AI-02` dan `AI-03`.
- [ ] Prettier pada file markdown kamus data lulus tanpa error.

### Dependencies

- Prasyarat: `DS-01` (Pemahaman Struktur Data Awal).
- Terkait: Menjadi prasyarat mutlak bagi `AI-02` (Model Relevansi) dan `AI-03` (Model Sentimen).

---

## [DS-04] Feature Engineering & Modeling Forecasting Permintaan (Moving Average vs Random Forest)

- **Labels:** `area:ds`, `priority:P2-side-quest`, `quest:side`
- **Priority:** `P2-side-quest`
- **Milestone:** `M2 (28 Nov–4 Des 2026)`
- **Target Path:** `notebooks`, `apps/ai-service/app/ml/forecasting/artifacts`

### Context

Untuk membantu Catering Si Kembar memperkirakan kebutuhan belanja bahan baku beberapa hari ke depan, diperlukan model peramalan (_demand forecasting_) berbasis data runtun waktu (_time series_). Sebagai bagian dari pemenuhan checklist Side Quest Data Science, tim harus melakukan rekayasa fitur (_feature engineering_), membangun model baseline sederhana (_Moving Average_), mengembangkan model pembelajaran mesin (_Random Forest Regressor_), melakukan hyperparameter tuning berbasis validasi waktu, serta membandingkan performa kedua model menggunakan metrik regresi standar (MAE, RMSE, WAPE).

### Scope

**In-Scope:**

- Rekayasa fitur runtun waktu: fitur lag (`lag_1`, `lag_7`), rolling statistics (`rolling_mean_7`, `rolling_std_7`), fitur kalender (hari dalam seminggu, tanggal, akhir pekan, hari libur nasional).
- Pembagian data berbasis urutan waktu (_chronological time-based split_ / _Timezone-aware cross validation_) untuk menghindari look-ahead bias.
- Pelatihan model baseline (Simple Moving Average / Exponential Smoothing).
- Pelatihan model machine learning Random Forest Regressor dengan hyperparameter tuning (GridSearchCV / TimeSeriesSplit).
- Evaluasi komparatif performa model sebelum dan sesudah tuning menggunakan metrik MAE, RMSE, dan WAPE.
- Serialisasi model terlatih terbaik ke format `joblib` di `apps/ai-service/app/ml/forecasting/artifacts/forecasting_rf.joblib`.
- Notebook lengkap di `notebooks/03_demand_forecasting.ipynb`.

**Out-of-Scope:**

- Pemodelan deep learning sekuensial yang rumit (seperti LSTM/Transformer) yang membutuhkan GPU besar dan data ribuan baris.
- Menjamin akurasi 100% pada operasional riil (hasil disampaikan sebagai estimasi pendukung keputusan).

### Business Rules

- Dilarang mengacak urutan data (_random shuffle_) pada tahap train-test split peramalan runtun waktu.
- Model harus dapat menangani kondisi hari tanpa pesanan (_zero-order days_) tanpa menghasilkan error numerik.
- Evaluasi metrik wajib disajikan dalam tabel perbandingan yang objektif di notebook dan README.

### API Contract

Tidak berlaku (tugas non-API). Menghasilkan model file biner serialisasi (`.joblib`) dan artefak metrik evaluasi.

### Acceptance Criteria

- [ ] Notebook `notebooks/03_demand_forecasting.ipynb` berhasil mengeksekusi pipeline rekayasa fitur dan pelatihan model.
- [ ] Tersedia tabel perbandingan metrik evaluasi (MAE, RMSE, WAPE) antara baseline Moving Average vs Random Forest (sebelum & sesudah tuning).
- [ ] Model Random Forest menunjukkan peningkatan akurasi atau stabilitas dibandingkan baseline Moving Average.
- [ ] File model serialisasi `apps/ai-service/app/ml/forecasting/artifacts/forecasting_rf.joblib` berhasil disimpan dan dapat di-_load_ kembali untuk prediksi.

### Technical Notes

- Batas waktu holdout data runtun waktu `[Perlu Konfirmasi Tim]`.
- Daftar kalender libur nasional dan hari besar keagamaan di Indonesia `[Perlu Konfirmasi Tim]`.

### DoD

- [ ] Notebook selesai dan terdokumentasi dengan penjelasan metrik matematis yang jelas.
- [ ] Berkas artefak model tersimpan dan siap diintegrasikan.
- [ ] Skrip validasi verifikasi prediksi pada data uji lulus tanpa error.

### Dependencies

- Prasyarat: `DS-01` (Dataset Runtun Waktu Bersih), `DS-03` (Data Sintetis Pelengkap).
- Terkait: Menjadi dasar bagi integrasi serving `DS-05`.

---

## [DS-05] Integrasi Pipeline Inferensi Forecasting ke `apps/ai-service`

- **Labels:** `area:ds`, `priority:P2-side-quest`, `quest:side`
- **Priority:** `P2-side-quest`
- **Milestone:** `M3 (5–11 Des 2026)`
- **Target Path:** `apps/ai-service/app/ml/forecasting`

### Context

Model peramalan permintaan yang telah dilatih dan dievaluasi di notebook harus dapat diakses secara online oleh backend Express monorepo. Tim Data Science bekerja sama dengan AI Engineering untuk mengemas pipeline inferensi model Random Forest ke dalam modul Python yang bersih di `apps/ai-service/app/ml/forecasting` dan mengekspos endpoint FastAPI dengan kontrak wire monorepo seragam (`{ data, meta }`, RFC 9457).

### Scope

**In-Scope:**

- Pembuatan modul Python inferensi: pemuatan model serialisasi `joblib` dari `apps/ai-service/app/ml/forecasting/artifacts/forecasting_rf.joblib`, pembuatan fitur lag secara on-the-fly, dan eksekusi prediksi runtun waktu ke depan (misal: proyeksi 1 s.d. 30 hari ke depan).
- Pembuatan router FastAPI di `apps/ai-service/app/ml/forecasting/router.py`.
- Endpoint prediksi permintaan porsi harian (`/api/v1/ml/forecast/demand`) dan metadata status model (`/api/v1/ml/forecast/metadata`).
- Skema validasi request dan response Pydantic yang selaras dengan envelope monorepo `{ data, meta }`.
- Penanganan kondisi batas: penanganan input riwayat kosong, konversi tipe data tanggal, dan pembatasan rentang prediksi maksimal 30 hari ke depan.
- Integrasi dokumentasi OpenAPI 3.1.0 di `/openapi.json` dan Scalar di `/docs` (fail-closed produksi `DOCS_ENABLED`).

**Out-of-Scope:**

- Pelatihan ulang model (_re-training_) otomatis di dalam container produksi.
- Pemanggilan endpoint langsung dari browser publik (akses dibatasi hanya untuk internal jaringan backend).

### Business Rules

- Prediksi peramalan hanya bersifat estimasi kuantitatif untuk membantu perencanaan belanja dapur.
- Angka hasil prediksi tidak boleh bernilai negatif (selalu dibatasi nilai minimum 0).
- Response wajib memuat metadata versi model dan tanggal eksekusi prediksi.
- Endpoint hanya boleh dipanggil dari jaringan internal VPS atau menyertakan `X-Internal-Token`.

### API Contract

#### Daftar Endpoint

| Method | Path                           | Fungsi                                                                                        | Autentikasi / Role                                                 |
| :----- | :----------------------------- | :-------------------------------------------------------------------------------------------- | :----------------------------------------------------------------- |
| `POST` | `/api/v1/ml/forecast/demand`   | Prediksi permintaan porsi harian ke depan (horizonDays 1..30) menggunakan model Random Forest | Autentikasi: Internal Network / `X-Internal-Token` dari `apps/api` |
| `GET`  | `/api/v1/ml/forecast/metadata` | Metadata versi model, metrik evaluasi terakhir, dan status batas data sintetis                | Autentikasi: Internal Network / `X-Internal-Token`                 |

#### Format Wire Contract Sukses

- `POST /api/v1/ml/forecast/demand` (Internal Service Call via FastAPI)
  - Request:
    ```json
    {
      "horizonDays": 7,
      "recentDailyOrders": [
        { "date": "2026-11-20", "totalPortions": 120 },
        { "date": "2026-11-21", "totalPortions": 150 },
        { "date": "2026-11-22", "totalPortions": 80 }
      ]
    }
    ```
  - Response `200 OK`:
    ```json
    {
      "data": {
        "modelName": "RandomForestDemandRegressor",
        "modelVersion": "1.0.0",
        "forecast": [
          {
            "date": "2026-11-23",
            "predictedPortions": 110,
            "confidenceInterval": { "lower": 95, "upper": 125 }
          },
          {
            "date": "2026-11-24",
            "predictedPortions": 130,
            "confidenceInterval": { "lower": 110, "upper": 150 }
          }
        ]
      },
      "meta": { "requestId": "0192f0c8-7b3a-7000-8000-000000000008" }
    }
    ```

- `GET /api/v1/ml/forecast/metadata`
  - Response `200 OK`:
    ```json
    {
      "data": {
        "modelName": "RandomForestDemandRegressor",
        "modelVersion": "1.0.0",
        "trainedAt": "2026-11-28T00:00:00.000Z",
        "metrics": {
          "mae": 14.2,
          "rmse": 18.7,
          "wape": 0.12
        },
        "features": ["lag_1", "lag_7", "rolling_mean_7", "day_of_week", "is_weekend"],
        "artifactPath": "apps/ai-service/app/ml/forecasting/artifacts/forecasting_rf.joblib"
      },
      "meta": { "requestId": "0192f0c8-7b3a-7000-8000-000000000009" }
    }
    ```

#### Standar Error RFC 9457 & Kode Status HTTP

Layanan mengembalikan kode status HTTP standar:

- `200 OK`: Prediksi berhasil dihitung atau metadata berhasil diambil.
- `400 Bad Request`: Format JSON tidak valid.
- `401 Unauthorized`: Kredensial token internal salah atau tidak ada.
- `403 Forbidden`: Akses ditolak karena bukan berasal dari internal service.
- `404 Not Found`: Model artefak tidak ditemukan pada path yang ditentukan.
- `422 Unprocessable Content`: Validasi skema Pydantic gagal (misal: horizonDays < 1 atau > 30, format tanggal salah).
- `500 Internal Server Error`: Kesalahan server internal saat kalkulasi inferensi.
- `503 Service Unavailable`: Layanan forecasting sedang mengalami pemuatan ulang model.

Contoh payload error RFC 9457 (`Content-Type: application/problem+json`):

```json
{
  "type": "https://datatracker.ietf.org/doc/html/rfc9457",
  "title": "Unprocessable Content",
  "status": 422,
  "detail": "Rentang horizonDays tidak valid. Nilai harus antara 1 dan 30.",
  "instance": "/api/v1/ml/forecast/demand",
  "requestId": "0192f0c8-7b3a-7000-8000-000000000008",
  "errors": [
    {
      "path": "horizonDays",
      "code": "value_error.range",
      "message": "horizonDays harus berada dalam rentang 1 hingga 30"
    }
  ]
}
```

#### Dokumentasi OpenAPI 3.1.0 & Scalar

Seluruh endpoint terdaftar dalam skema OpenAPI 3.1.0 di `/openapi.json` dan disajikan via Scalar UI di `/docs` (fail-closed produksi `DOCS_ENABLED`).

### Acceptance Criteria

- [ ] Seluruh 2 endpoint forecasting (`/demand` dan `/metadata`) terdaftar pada tabel kontrak API dan terimplementasi.
- [ ] Endpoint FastAPI berhasil memuat model dan mengembalikan proyeksi peramalan dalam format JSON valid `{ data, meta }`.
- [ ] Waktu respon inferensi di bawah 200ms pada lingkungan pengujian lokal.
- [ ] Pengujian Pytest pada modul `apps/ai-service/app/ml/forecasting` lulus dengan cakupan pengujian memadai.
- [ ] Input horizon negatif atau lebih dari 30 hari menghasilkan error validasi Pydantic RFC 9457 `422 Unprocessable Content`.
- [ ] Dokumentasi endpoint OpenAPI 3.1.0 tampil di Scalar `/docs`.

### Technical Notes

- Pemasangan dependensi `scikit-learn` pada sub-package `apps/ai-service` menggunakan `uv` `[Perlu Konfirmasi Tim]`.
- Lokasi penyimpanan artefak model biner di `apps/ai-service/app/ml/forecasting/artifacts/` `[Perlu Konfirmasi Tim]`.

### DoD

- [ ] Modul router dan service forecasting terintegrasi rapi di `apps/ai-service`.
- [ ] Seluruh unit test Pytest lulus tanpa peringatan kritis.
- [ ] Endpoint terdaftar pada dokumentasi OpenAPI 3.1.0 FastAPI Scalar `/docs`.

### Dependencies

- Prasyarat: `DS-04` (Artefak Model Terlatih), `AI-01` (FastAPI Server Foundation).
- Terkait: Dikonsumsi oleh `FS-08` (Modul Dasbor Analitik).

---

## [DS-06] Spesifikasi KPI Dasbor Bisnis & Audit Akurasi Data Akhir

- **Labels:** `area:ds`, `priority:P1-mvp`, `quest:main`, `quest:side`
- **Priority:** `P1-mvp`
- **Milestone:** `M4 (12–20 Des 2026)`
- **Target Path:** `notebooks`, `data`

### Context

Mendekati fase validasi akhir dan demonstrasi capstone, tim Data Science bertanggung jawab memastikan bahwa seluruh angka, kalkulasi KPI pada dasbor web, estimasi bahan baku, serta keluaran model machine learning memiliki integritas dan akurasi yang dapat dipertanggungjawabkan. Diperlukan audit data komprehensif untuk memverifikasi tidak adanya kebocoran data (_leakage_), ketiadaan data sensitif yang tidak sengaja tertinggal, serta keselarasan formula KPI antara dokumen spesifikasi dan kode backend.

### Scope

**In-Scope:**

- Penyusunan spesifikasi teknis formula perhitungan seluruh KPI bisnis (Revenue, Rata-rata Porsi, Menu Terfavorit, Tingkat Retensi/Repeat Order).
- Audit validasi data transaksi: verifikasi konsistensi relasi order, invoice, dan resep bahan pada skema database.
- Pemeriksaan keakuratan kalkulasi agregasi pada endpoint analitik Express vs hasil perhitungan manual di Python.
- Verifikasi akhir kepatuhan privasi data: memastikan tidak ada kebocoran data pelanggan riil atau file secret di repositori.
- Penyusunan laporan ringkasan kualitas data dan temuan akhir (_Data Integrity & Accuracy Report_).

**Out-of-Scope:**

- Mengubah formula bisnis yang telah disepakati tanpa persetujuan tim.
- Evaluasi sistem penagihan di luar pencatatan data aplikasi katering.

### Business Rules

- Seluruh formula KPI harus memiliki definisi matematis yang eksplisit dan terdokumentasi.
- Jika ditemukan inkonsistensi data antara database transaksional dan hasil analitik, temuan wajib didokumentasikan beserta akar penyebabnya.
- Audit wajib memverifikasi penandaan seluruh data buatan (`is_synthetic = true`).

### API Contract

Tidak berlaku (tugas non-API). Menghasilkan dokumen audit kualitas data dan catatan verifikasi akurasi.

### Acceptance Criteria

- [ ] Tersedia dokumen spesifikasi formula KPI yang diadopsi secara konsisten oleh tim Full-Stack.
- [ ] Seluruh data pada pengujian demonstrasi akhir lolos audit integritas data (0 inkonsistensi foreign key atau missing fields).
- [ ] Perhitungan total pendapatan dan porsi pada dasbor terbukti cocok 100% dengan rekap database.
- [ ] Tidak ada berkas PII atau rahasia yang tertinggal di folder data proyek.

### Technical Notes

- Validasi kepuasan PIC UMKM terhadap kesesuaian formula KPI bisnis `[Menunggu Konfirmasi PIC]`.
- Persetujuan format pelaporan audit data akhir `[Perlu Konfirmasi Tim]`.

### DoD

- [ ] Dokumen audit akurasi data selesai disusun.
- [ ] Verifikasi silang angka analitik bersama tim Full-Stack berhasil disepakati.
- [ ] Repositori bersih dari file sampah atau checkpoint notebook lokal.

### Dependencies

- Prasyarat: `DS-02` (EDA), `FS-05` & `FS-06` (Data Transaksi), `FS-08` (Dasbor Analitik), `AI-06` (AI Business Insight).
- Terkait: Menjadi bukti kesiapan rilis pada demonstrasi akhir capstone.
