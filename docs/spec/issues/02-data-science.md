# Spesifikasi Teknis: Data Science (`02-data-science.md`)

Berkas ini memuat spesifikasi teknis lengkap untuk 6 issue area Data Science (`DS-01` s.d. `DS-06`) yang telah diselaraskan penuh dengan Asah 2026 Project Plan – A26-CS105, mencakup pengumpulan & anonimisasi data UMKM (tanpa PII/gaji), EDA 5 pertanyaan bisnis sekaligus penguncian definisi KPI dasbor sebelum M3, kamus data & generator sintetis berlabel `is_synthetic`, pemodelan forecasting permintaan per menu (evaluasi objektif Moving Average vs Random Forest), integrasi serving inferensi per menu ke `apps/ai-service`, serta verifikasi implementasi KPI & audit akurasi data akhir.

---

## [DS-01] Pengumpulan, Anonimisasi & Data Wrangling Data UMKM

- **Labels:** `area:ds`, `priority:P0-blocker`, `quest:main`
- **Priority:** `P0-blocker`
- **Klasifikasi Project Plan:** Wajib (Main Quest DS: Pengumpulan, Validasi, Anonimisasi & Wrangling Data)
- **Milestone:** `M1: Rancangan Disepakati (21–27 Nov 2026)`
- **Penanggung Jawab (Project Plan):** Chaviela Nazwa Syaqiba, Rio Andika Andriansyah
- **Target Path:** `data/raw` (lokal / `.gitignore`), `notebooks/01_data_wrangling.ipynb`

### Context

Catering Si Kembar mencatat transaksi historis secara terpisah di Google Spreadsheet dan nota fisik. Sesuai Project Plan A26-CS105, tim Data Science meminta ekspor rekap Spreadsheet pesanan yang dianonimkan sebagai **data primer** (dengan izin PIC, tanpa data gaji dan tanpa identitas pribadi pelanggan), memeriksa kualitas data (nilai kosong, duplikat, outlier, dan format tanggal) sebelum analisis, serta menyusun pipeline wrangling yang bersih dan dapat direproduksi. Jika data primer dari PIC masih terbatas pada M1, proses diselaraskan dengan data sintetis berlabel (`DS-03`) yang disetujui PIC.

### Scope

**Requirement Wajib (Project Plan):**

- Pengumpulan & inventarisasi data primer UMKM (daftar menu, bahan baku, resep, dan ekspor rekap Spreadsheet pesanan dengan izin PIC) pada folder lokal terisolasi (`data/raw/` yang diabaikan Git).
- **Anonimisasi ketat:** menghapus/menyamarkan seluruh PII pelanggan (nama lengkap → `CUST_001`, nomor telepon disamarkan/dihapus, alamat rumah privat dihapus atau dibatasi level kota/kecamatan) serta memastikan **tidak ada data gaji karyawan** atau nomor rekening yang masuk dataset.
- Pemeriksaan kualitas data (_data assessment_): nilai kosong (_missing values_), duplikat, outlier porsi/harga, serta format tanggal yang tidak seragam.
- Pembersihan data (_data cleaning_) beserta log transformasi terdokumentasi di `notebooks/01_data_wrangling.ipynb` dan ringkasan kualitas data di README.

**Rekomendasi Teknis / Implementasi:**

- Standarisasi format tanggal ke ISO `YYYY-MM-DD`, penamaan menu/satuan baku konsisten dengan `FS-02`/`FS-04`, dan simpan dataset bersih lokal dalam format CSV/Parquet.
- Beri kolom `is_synthetic = false` pada seluruh data primer UMKM yang telah dianonimkan agar selaras skema dengan data cadangan dari `DS-03`.

**Out-of-Scope:**

- Melakukan commit data mentah UMKM (`data/raw/*`) atau data ber-PII ke repositori Git.
- Menghapus transaksi anomali yang sah secara bisnis tanpa catatan alasan rasional.

### Business Rules

- Dilarang keras menyimpan atau mempublikasikan nama asli pelanggan, nomor telepon asli, alamat lengkap, rekening bank, maupun data gaji karyawan di repositori.
- Setiap baris data primer diberi `is_synthetic = false`; data buatan dilarang dicampur tanpa kolom penanda `is_synthetic = true`.
- Transaksi dengan porsi `<= 0` atau harga invalid tanpa keterangan pembatalan ditandai sebagai _invalid record_ dalam log pembersihan.

### API Contract

Tidak berlaku (tugas non-API). Menghasilkan notebook wrangling `notebooks/01_data_wrangling.ipynb` dan dataset bersih teranonimisasi lokal.

### Acceptance Criteria

- [ ] Notebook `notebooks/01_data_wrangling.ipynb` dapat dijalankan ulang dari awal hingga akhir (_reproducible_) tanpa error.
- [ ] Audit privasi membuktikan 0 baris dataset bersih mengandung nama asli pelanggan, nomor telepon riil, alamat privat lengkap, atau data gaji.
- [ ] Seluruh nilai kosong, duplikat, outlier, dan ketidakkonsistenan format tanggal diperiksa, ditangani, dan dicatat dalam log transformasi serta ringkasan kualitas data di README.
- [ ] Format tanggal terstandarisasi (`YYYY-MM-DD`) dan kolom kritis (`order_date`, `menu_name`, `portions`, `total_price`, `is_synthetic`) valid tanpa nilai kosong.
- [ ] `git status` bersih dari berkas data mentah UMKM (`data/raw/*`).

### Keputusan yang Membutuhkan Konfirmasi (PIC / Tim)

- `[Menunggu Konfirmasi PIC]` Izin tertulis/chat ekspor rekap Google Spreadsheet pesanan, daftar resep/takaran, dan persetujuan pemakaian data teranonimisasi untuk demonstrasi capstone.
- `[Perlu Konfirmasi Tim]` Penetapan ambang batas outlier porsi ekstrem (misal pesanan besar > 1000 porsi) dan aturan pemetaan nama menu yang ditulis tidak konsisten di Spreadsheet.

### DoD

- [ ] Notebook `notebooks/01_data_wrangling.ipynb` selesai, bersih, dan terdokumentasi dalam Bahasa Indonesia.
- [ ] Ringkasan kualitas dataset siap dimasukkan ke README proyek.
- [ ] Tidak ada berkas PII atau `data/raw/*` yang ter-commit ke Git.

### Dependencies

- **Prasyarat:** Izin akses data & ekspor rekap Spreadsheet dari PIC Catering Si Kembar.
- **Terkait:** Input wajib bagi `DS-02` (EDA & Definisi KPI), `DS-03` (Kamus Data & Sintetis), dan `DS-04` (Forecasting).

---

## [DS-02] EDA 5 Pertanyaan Bisnis, Definisi KPI Dasbor, Visualisasi & Rekomendasi Operasional

- **Labels:** `area:ds`, `priority:P1-mvp`, `quest:main`, `quest:side`
- **Priority:** `P1-mvp`
- **Klasifikasi Project Plan:** Wajib (Main Quest DS: Pengolahan & Analisis 5 Pertanyaan Bisnis, Temuan & Rekomendasi) & Fondasi Side Quest DS (**Penguncian Definisi KPI Dasbor sebelum integrasi `FS-08` di M3**)
- **Milestone:** `M2: Fitur Inti Tersedia (28 Nov–4 Des 2026)`
- **Penanggung Jawab (Project Plan):** Chaviela Nazwa Syaqiba
- **Target Path:** `notebooks/02_eda_business_questions.ipynb`, `docs/` atau `data/dictionary/`

### Context

Sesuai Project Plan A26-CS105, analisis eksploratif (EDA) wajib menjawab **5 pertanyaan bisnis utama** Catering Si Kembar: (1) Menu favorit, (2) Jumlah porsi, (3) Waktu ramai pemesanan, (4) Pola dan kepatuhan pembayaran, serta (5) Bahan baku yang paling banyak dikonsumsi, lalu membandingkan hasilnya dengan rekap Spreadsheet asli yang dianonimkan dan diizinkan PIC. Selain itu, agar integrasi Dasbor Analitik (`FS-08`) pada M3 tidak terhambat atau menghasilkan angka yang berbeda-beda antar tim, **spesifikasi dan formula matematis KPI Dasbor wajib didefinisikan dan dikunci di akhir M2 pada issue ini** sebelum implementasi dashboard dimulai.

### Scope

**Requirement Wajib (Project Plan):**

- Eksplorasi mendalam dan visualisasi di `notebooks/02_eda_business_questions.ipynb` untuk menjawab seluruh **5 pertanyaan bisnis**:
  1. Menu favorit (membedakan _order count_ / frekuensi pesan vs _portion volume_ / total porsi).
  2. Distribusi dan rata-rata jumlah porsi per pesanan.
  3. Pola waktu ramai (hari dalam seminggu, minggu dalam bulan, musim/periode puncak).
  4. Pola pembayaran (rasio lunas vs DP/piutang dan ketepatan pelunasan).
  5. Bahan baku utama paling banyak dikonsumsi (berdasarkan pemetaan resep standar).
- Perbandingan dan validasi hasil analisis dengan rekap Spreadsheet asli yang dianonimkan dan diizinkan PIC.
- Penyusunan ringkasan temuan (_key findings_) dan rekomendasi operasional praktis berbasis bukti data.
- **Definisi & Penguncian Formula KPI Dasbor (Pra-Integrasi `FS-08` M3):** Dokumen spesifikasi formula KPI (Total Pesanan, Total Porsi, Total Omzet/Revenue, Rata-rata Porsi, Menu Terfavorit, Rasio Pelunasan/Piutang, Distribusi Sentimen, Estimasi Bahan Baku Forecasting) termasuk definisi filter periode & status, serta pemisahan data `is_synthetic`.

**Rekomendasi Teknis / Implementasi:**

- Ekspor gambar visualisasi penting untuk bahan README dan presentasi akhir.
- Simpan dokumen spesifikasi formula KPI di `data/dictionary/kpi_definitions.md` (atau bagian khusus di `data/dictionary/`) agar langsung dirujuk oleh tim Full-Stack pada `FS-08` dan tim AI pada `AI-06`.

**Out-of-Scope:**

- Pemodelan forecasting prediktif (dikerjakan pada `DS-04`).
- Implementasi antarmuka grafik web dinamis (dikerjakan pada `FS-08`).

### Business Rules

- Seluruh rekomendasi operasional wajib ditopang angka dan visualisasi EDA yang terverifikasi.
- Perhitungan menu favorit wajib membedakan frekuensi pesanan (_order count_) dan akumulasi porsi (_portion volume_).
- Jika data sintetis digunakan sebagai pelengkap, hasil analisis wajib memisahkan/menandai secara eksplisit porsi data asli vs data `is_synthetic = true`.
- Formula KPI yang disepakati di akhir M2 menjadi kontrak tunggal bagi implementasi `FS-08` (M3), `AI-06` (M3), dan audit akhir `DS-06` (M4).

### API Contract

Tidak berlaku (tugas non-API). Menghasilkan notebook `notebooks/02_eda_business_questions.ipynb` dan dokumen definisi KPI terkunci untuk tim Full-Stack (`FS-08`) & AI (`AI-06`).

### Acceptance Criteria

- [ ] Notebook `notebooks/02_eda_business_questions.ipynb` berjalan bersih tanpa error dan menjawab seluruh 5 pertanyaan bisnis secara lengkap dengan grafik berlabel jelas.
- [ ] Hasil EDA telah dibandingkan dengan rekap Spreadsheet asli yang dianonimkan dan diizinkan PIC, serta selisih/batas data dicatat jelas.
- [ ] Tersedia dokumen spesifikasi formula matematis KPI Dasbor yang disepakati bersama tim Full-Stack **sebelum implementasi `FS-08` dimulai pada M3**.
- [ ] Tersedia bagian temuan kunci dan rekomendasi operasional yang relevan dengan praktik F&B katering.

### Keputusan yang Membutuhkan Konfirmasi (PIC / Tim)

- `[Menunggu Konfirmasi PIC]` Konfirmasi kewajaran temuan pola hari ramai, menu terlaris, dan daftar metrik KPI utama yang ingin dipantau pengelola di dasbor web.
- `[Perlu Konfirmasi Tim]` Penandatanganan/kesepakatan bersama definisi matematis KPI (misal: apakah Revenue menghitung seluruh order `CONFIRMED` atau hanya pembayaran aktual `Payment` yang sudah masuk) antara DS (`DS-02`), Full-Stack (`FS-08`), dan AI (`AI-06`).

### DoD

- [ ] Notebook EDA selesai dieksekusi, bersih, dan terdokumentasi.
- [ ] Dokumen definisi KPI terkunci dan diterima tim Full-Stack (`FS-08`) sebelum masuk M3.
- [ ] Ringkasan temuan 5 pertanyaan bisnis siap dimuat ke README proyek.

### Dependencies

- **Prasyarat:** `DS-01` (Dataset Bersih Teranonimisasi), `DS-03` (Kamus Data & Resep/Satuan).
- **Terkait:** Menjadi **prasyarat wajib** bagi implementasi Dasbor Analitik `FS-08` (M3), input metrik `AI-06` (M3), dan bahan verifikasi audit akhir `DS-06` (M4).

---

## [DS-03] Kamus Data, Generator Data Sintetik (`is_synthetic`) & Paket Dataset untuk Gen AI

- **Labels:** `area:ds`, `priority:P0-blocker`, `quest:main`, `quest:side`
- **Priority:** `P0-blocker`
- **Klasifikasi Project Plan:** Wajib (Kamus Data, Data Sintetis Berlabel `is_synthetic` sebagai cadangan, Paket Dataset Model Relevansi 2 Kelas) & Tambahan (Dataset Sentimen & Forecasting)
- **Milestone:** `M1: Rancangan Disepakati (21–27 Nov 2026)`
- **Penanggung Jawab (Project Plan):** Rio Andika Andriansyah, Chaviela Nazwa Syaqiba
- **Target Path:** `data/dictionary`, `data/synthetic`

### Context

Keterbatasan data historis UMKM (khususnya data teks pertanyaan pelanggan dan feedback ulasan) merupakan risiko utama yang diidentifikasi dalam Project Plan A26-CS105. Tim Data Science wajib menyusun **Kamus Data (_Data Dictionary_)** resmi yang menyelaraskan nama kolom/satuan lintas tim, membangun **generator data sintetis berlabel `is_synthetic = true`** dengan metodologi terdokumentasi dan disetujui PIC sebagai cadangan simulasi, serta menyiapkan paket dataset latih/uji terpisah bersih tanpa kebocoran data (_data leakage_) untuk model relevansi 2 kelas (`AI-02`), analisis sentimen (`AI-03`), dan peramalan permintaan per menu (`DS-04`).

### Scope

**Requirement Wajib (Project Plan):**

- Penyusunan Kamus Data resmi di `data/dictionary/data_dictionary.md`: definisi tabel, kolom, tipe data, rentang nilai valid, satuan baku bahan pangan (`gram`, `kg`, `ml`, `liter`, `butir`, dll.), dan faktor konversi yang selaras dengan `FS-02` & `FS-04`.
- Pembuatan generator data sintetis deterministik (`data/synthetic/generate_synthetic_data.py`) yang menghasilkan:
  1. Dataset simulasi pesanan historis **per menu** (untuk cadangan EDA/forecasting bila rekap asli terbatas).
  2. Paket dataset klasifikasi **relevansi 2 kelas** (`relevant` vs `out_of_domain`) untuk `AI-02` (tanpa klasifikasi multi-intent).
  3. Paket dataset analisis **sentimen 2 kelas** (`positive` vs `negative`) untuk `AI-03`.
- **Penandaan wajib `is_synthetic = true`** pada 100% baris data buatan, disertai dokumentasi penjelasan proses pembuatannya (distribusi, asumsi, sumber pola) untuk README proyek.
- **Pemisahan data anti-leakage:** pembagian `train`/`test` (stratified untuk teks AI; kronologis untuk runtun waktu forecasting) yang menjamin tidak ada kebocoran data uji ke tahap pelatihan atau perancangan aturan generator.

**Rekomendasi Teknis / Implementasi:**

- Gunakan _fixed random seed_ pada generator agar paket dataset 100% reproducible.
- Sertakan variasi bahasa Indonesia informal/percakapan WhatsApp dan kalimat campuran (_mixed sentiment_ / pertanyaan ambang batas) pada data uji untuk menguji ketangguhan model `AI-02` & `AI-03`.

**Out-of-Scope:**

- Menyamarkan data sintetis sebagai transaksi atau ulasan nyata pelanggan UMKM (pelanggaran ketat guardrail Project Plan).
- Memasukkan PII nyata pelanggan atau data gaji ke dalam generator/dataset.

### Business Rules

- 100% baris data buatan wajib memiliki atribut `is_synthetic = true` dan **tidak boleh diklaim sebagai transaksi atau feedback nyata**.
- Rentang porsi, harga, dan daftar menu pada data sintetis mengacu pada katalog/resep yang dikonfirmasi atau disetujui PIC sebagai simulasi.
- Data uji (_holdout test set_) terpisah secara ketat dari data latih (_zero data leakage_).

### API Contract

Tidak berlaku (tugas non-API). Menghasilkan `data/dictionary/data_dictionary.md`, skrip `data/synthetic/generate_synthetic_data.py`, dan paket dataset siap pakai (`train_relevance.csv`, `test_relevance.csv`, `train_sentiment.csv`, `test_sentiment.csv`, serta data pesanan simulasi per menu).

### Acceptance Criteria

- [ ] `data/dictionary/data_dictionary.md` memuat definisi lengkap kolom, tipe data, satuan baku bahan, dan aturan konversi yang selaras dengan `FS-02` dan `FS-04`.
- [ ] `generate_synthetic_data.py` berjalan deterministik (dengan seed tetap) dan 100% baris keluarannya memiliki kolom `is_synthetic = true`.
- [ ] Metode pembuatan data sintetis, asumsi distribusi, dan pembatasan klaim simulasi terdokumentasi lengkap untuk dimasukkan ke README.
- [ ] Paket dataset relevansi 2 kelas (`relevant`/`out_of_domain`) dan sentimen 2 kelas (`positive`/`negative`) lolos uji skema dan verifikasi _zero data leakage_ (0 duplikasi/overlap antara train dan test).
- [ ] Penggunaan data sintetis sebagai cadangan simulasi mendapat persetujuan PIC.

### Keputusan yang Membutuhkan Konfirmasi (PIC / Tim)

- `[Menunggu Konfirmasi PIC]` Persetujuan penggunaan data sintetis berlabel `is_synthetic` sebagai data simulasi cadangan jika rekap Spreadsheet atau feedback historis terbatas.
- `[Perlu Konfirmasi Tim]` Kesepakatan proporsi split train/test (misal 80:20) dan jumlah sampel minimal per kelas antara DS (`DS-03`) dan AI Engineering (`AI-02`, `AI-03`).

### DoD

- [ ] Kamus data, skrip generator, dan dokumentasi metodologi data sintetis tersimpan rapi di `data/`.
- [ ] Paket dataset terverifikasi siap dikonsumsi oleh `AI-02`, `AI-03`, dan `DS-04`.
- [ ] `npm run format:check` dan linting Python lulus tanpa error.

### Dependencies

- **Prasyarat:** `DS-01` (Struktur Data Awal UMKM).
- **Terkait:** Prasyarat langsung bagi `AI-02` (Model Relevansi 2 Kelas), `AI-03` (Model Sentimen), `DS-04` (Forecasting), dan selaras satuan dengan `FS-02` / `FS-04`.

---

## [DS-04] Feature Engineering & Modeling Forecasting Permintaan per Menu (Moving Average vs Random Forest)

- **Labels:** `area:ds`, `priority:P2-side-quest`, `quest:side`
- **Priority:** `P2-side-quest` _(fitur tambahan — tidak boleh menunda alur utama)_
- **Klasifikasi Project Plan:** Tambahan (Side Quest DS: Forecasting Permintaan Menu & Estimasi Kebutuhan Bahan Baku — Baseline Moving Average vs Random Forest)
- **Milestone:** `M2: Fitur Inti Tersedia (28 Nov–4 Des 2026)`
- **Penanggung Jawab (Project Plan):** Rio Andika Andriansyah, Chaviela Nazwa Syaqiba
- **Target Path:** `notebooks/03_demand_forecasting.ipynb`, `apps/ai-service/app/ml/forecasting/artifacts`

### Context

Untuk membantu Catering Si Kembar memperkirakan **kebutuhan bahan baku** beberapa hari ke depan, diperlukan model **forecasting permintaan per menu** (bukan hanya agregat total porsi) sehingga proyeksi porsi per menu dapat langsung dikalikan dengan resep standar terkonfirmasi (`FS-04`). Sesuai Project Plan A26-CS105, tim wajib membandingkan **baseline Moving Average** dan **Random Forest** secara **objektif** melalui pembagian data kronologis dan validasi berbasis waktu menggunakan metrik MAE, RMSE, atau WAPE, mengevaluasi pengaruh fitur lag & rolling serta hyperparameter tuning (sebelum vs sesudah optimasi), dan menyatakan batas keterbatasan data/simulasi secara transparan.

### Scope

**Requirement Wajib (Project Plan untuk Fitur Forecasting):**

- Eksperimen lengkap pada `notebooks/03_demand_forecasting.ipynb` dengan target **prediksi permintaan porsi per menu** (untuk mendukung kalkulasi estimasi kebutuhan bahan baku di `FS-08`).
- Pembagian data **kronologis** (_time-based split_) dan validasi berbasis waktu (_TimeSeriesSplit_ / _walk-forward validation_) tanpa _random shuffle_ untuk mencegah _look-ahead bias_.
- Rekayasa fitur runtun waktu: fitur **lag** (`lag_1`, `lag_7`), **rolling statistics** (`rolling_mean_7`, `rolling_std_7`), fitur kalender (hari dalam minggu, akhir pekan, tanggal/bulan), serta fitur identitas/kategori menu.
- **Evaluasi komparatif yang objektif:**
  1. Baseline **Moving Average** vs **Random Forest** pada periode uji kronologis yang sama menggunakan **MAE, RMSE, dan WAPE**.
  2. **Studi ablasi fitur:** perbandingan performa Random Forest **tanpa vs dengan fitur lag & rolling**.
  3. **Evaluasi optimasi:** perbandingan performa **sebelum vs sesudah hyperparameter tuning** berbasis validasi waktu.
- Pemilihan model terbaik secara **objektif berdasarkan data** (apabila pada data historis yang pendek Moving Average lebih unggul atau setara dengan Random Forest, hal tersebut dilaporkan apa adanya disertai analisis teknis!).
- Serialisasi artefak model terpilih (`joblib` atau konfigurasi baseline) + metadata metrik evaluasi untuk `DS-05` di `apps/ai-service/app/ml/forecasting/artifacts/`.
- Pernyataan eksplisit mengenai batas data (jumlah periode, porsi data `is_synthetic`, dan bahwa hasil bukan jaminan akurasi operasional nyata).

**Rekomendasi Teknis / Implementasi:**

- Untuk menu dengan riwayat sangat jarang (_sparse_), sediakan strategi cadangan terukur (misal peramalan top-N menu utama + kategori lainnya, atau dekomposisi proporsi historis per menu) dan dokumentasikan asumsinya.
- Tangani hari tanpa pesanan (_zero-order days_) secara konsisten pada seri waktu harian per menu.

**Out-of-Scope:**

- Model deep learning sekuensial berat (LSTM/Transformer) yang tidak proporsional untuk volume data UMKM.
- Klaim jaminan akurasi prediksi untuk keputusan pembelian komersial otomatis tanpa validasi pengguna.

### Business Rules

- **Objektivitas Evaluasi:** Dilarang memanipulasi split atau memaksakan Random Forest tampak lebih unggul dari Moving Average; pemilihan model dan analisis error wajib 100% jujur dan reproducible.
- **Tanpa Kebocoran Waktu:** Dilarang keras melakukan _random shuffle_ atau menghitung fitur rolling/scaling menggunakan data masa depan (_test set_).
- **Granularitas Per Menu:** Keluaran model harus menghasilkan prediksi porsi yang terpetakan ke `menuId`/`menu_name` agar dapat digabung dengan resep standar (`FS-04`) menjadi estimasi bahan baku.
- **Transparansi Data:** Jika pelatihan memakai data sintetis (`is_synthetic = true`), status tersebut wajib tersimpan dalam metadata artefak dan ditulis jelas di README.

### API Contract

Tidak berlaku (tugas non-API). Menghasilkan notebook `notebooks/03_demand_forecasting.ipynb`, artefak model terpilih di `apps/ai-service/app/ml/forecasting/artifacts/`, dan berkas metadata evaluasi (`metrics.json`).

### Acceptance Criteria

- [ ] Notebook `notebooks/03_demand_forecasting.ipynb` reproducible tanpa error dan menghasilkan prediksi permintaan **per menu**.
- [ ] Pembagian data dilakukan secara kronologis dan validasi menggunakan skema berbasis waktu (_zero look-ahead bias_).
- [ ] Tersedia tabel evaluasi **objektif** (MAE, RMSE, WAPE) yang membandingkan: (a) Moving Average vs Random Forest, (b) dengan vs tanpa fitur lag & rolling, serta (c) sebelum vs sesudah hyperparameter tuning—lengkap dengan analisis alasan pemilihan model pemenang di notebook & README.
- [ ] Skenario hari tanpa pesanan (_zero-order days_) dan riwayat pendek tertangani tanpa error numerik (NaN/Inf).
- [ ] Artefak model pemenang beserta metadata evaluasi (termasuk flag `is_synthetic` dan batas data) tersimpan di `apps/ai-service/app/ml/forecasting/artifacts/` dan terbukti dapat dimuat kembali untuk inferensi di `DS-05`.

### Keputusan yang Membutuhkan Konfirmasi (PIC / Tim)

- `[Menunggu Konfirmasi PIC]` Daftar menu utama yang paling prioritas untuk diprediksi kebutuhan bahan bakunya pada demonstrasi.
- `[Perlu Konfirmasi Tim]` Penetapan panjang jendela holdout kronologis (misal 14 atau 30 hari terakhir) dan strategi agregasi untuk menu berfrekuensi sangat rendah (_sparse_).

### DoD

- [ ] Notebook `notebooks/03_demand_forecasting.ipynb` lengkap dengan interpretasi metrik objektif dan analisis batas data.
- [ ] Artefak model & metadata evaluasi tersimpan dan terverifikasi bisa di-load oleh Python 3.12 (`apps/ai-service`).
- [ ] Ringkasan hasil perbandingan model & batas data sintetis siap dicantumkan di README proyek.

### Dependencies

- **Prasyarat:** `DS-01` (Dataset Runtun Waktu Bersih), `DS-03` (Data Sintetis Pelengkap & Kamus Data).
- **Terkait:** Menjadi input langsung bagi integrasi serving `DS-05` dan tampilan estimasi bahan baku pada `FS-08`.

---

## [DS-05] Integrasi Pipeline Inferensi Forecasting per Menu ke `apps/ai-service`

- **Labels:** `area:ds`, `priority:P2-side-quest`, `quest:side`
- **Priority:** `P2-side-quest` _(fitur tambahan — tidak boleh menunda alur utama sebelum feature freeze akhir M3)_
- **Klasifikasi Project Plan:** Tambahan (Side Quest DS: Penyajian Model Forecasting Permintaan Menu via FastAPI untuk Estimasi Bahan Baku)
- **Milestone:** `M3: Alur Utama Selesai & Feature Freeze (5–11 Des 2026)`
- **Penanggung Jawab (Project Plan):** Rio Andika Andriansyah, Chaviela Nazwa Syaqiba
- **Target Path:** `apps/ai-service/app/ml/forecasting`

### Context

Agar hasil prediksi permintaan per menu dari `DS-04` dapat dikonsumsi secara online oleh backend Express (`FS-08`) lalu digabungkan dengan resep standar (`FS-04`) menjadi estimasi kebutuhan bahan baku, pipeline inferensi dikemas menjadi modul Python bersih di `apps/ai-service/app/ml/forecasting` dengan kontrak REST FastAPI OpenAPI 3.1.0 (`{ data, meta }`, RFC 9457, `X-Internal-Token`). Modul juga wajib menangani kondisi riwayat data kosong atau terlalu sedikit dengan pesan jelas serta menyatakan batas data sintetis secara eksplisit sesuai Rencana Pengujian Project Plan.

### Scope

**Requirement Wajib (Project Plan untuk Fitur Forecasting Serving):**

- Modul inferensi Python di `apps/ai-service/app/ml/forecasting/` yang memuat artefak **model pemenang hasil evaluasi objektif `DS-04`** (Random Forest atau Moving Average baseline), membangun fitur lag/rolling secara on-the-fly, dan memprediksi permintaan **per menu** untuk horizon 1 s.d. 30 hari ke depan.
- Endpoint FastAPI:
  1. `POST /api/v1/ml/forecast/demand`: menerima `horizonDays` dan riwayat harian per menu (`recentMenuOrders`), mengembalikan proyeksi porsi **per menu per tanggal** serta ringkasan total porsi per menu (siap langsung dipetakan ke kalkulator bahan `FS-04` oleh backend Express `FS-08`).
  2. `GET /api/v1/ml/forecast/metadata`: mengembalikan nama model terpilih, versi, metrik perbandingan (`MAE`, `RMSE`, `WAPE` Moving Average vs Random Forest), flag `isSyntheticTrained`, dan pernyataan batas data.
- **Penanganan data kosong atau terlalu sedikit:** jika `recentMenuOrders` kosong atau jumlah hari historis kurang dari batas minimum pembentuk lag (misal < 7 hari), kembalikan pesan yang jelas (HTTP `422` RFC 9457 atau peringatan terstruktur `insufficientData` sesuai kesepakatan tim) tanpa crash atau nilai negatif/NaN.

**Rekomendasi Teknis / Implementasi:**

- Gunakan Pydantic strict (`extra="forbid"`) konsisten dengan `AI-01`, proteksi `verify_internal_token` (`X-Internal-Token`), dan daftarkan di OpenAPI 3.1.0 Scalar `/docs`.
- Pastikan seluruh angka prediksi non-negatif (`>= 0`) dan dibulatkan wajar ke integer porsi untuk kebutuhan operasional.

**Out-of-Scope:**

- Kalkulasi resep/konversi bahan baku di dalam `apps/ai-service` (penggabungan hasil forecasting per menu dengan resep terkonfirmasi dilakukan oleh backend Express `FS-08` memakai service `FS-04` agar sumber resep tetap tunggal di PostgreSQL).
- Pelatihan ulang model otomatis (_auto-retraining_) di dalam container produksi.
- Akses langsung dari browser publik.

### Business Rules

- Prediksi merupakan estimasi kuantitatif pendukung keputusan, bukan jaminan akurasi operasional.
- Nilai `predictedPortions` selalu `>= 0`.
- Respons wajib menyertakan metadata model terpilih, `isSyntheticTrained`, dan `dataDisclaimer`.
- Endpoint hanya dapat dipanggil oleh internal backend Express (`apps/api`) dengan `X-Internal-Token` valid.

### API Contract

#### Daftar Endpoint

| Method | Path                           | Fungsi                                                                                      | Autentikasi / Role                    |
| :----- | :----------------------------- | :------------------------------------------------------------------------------------------ | :------------------------------------ |
| `POST` | `/api/v1/ml/forecast/demand`   | Prediksi permintaan porsi **per menu** untuk horizon `1..30` hari ke depan                  | Internal Network / `X-Internal-Token` |
| `GET`  | `/api/v1/ml/forecast/metadata` | Metadata model pemenang (`DS-04`), metrik evaluasi komparatif, & status batas data sintetis | Internal Network / `X-Internal-Token` |

#### Contoh Wire Contract Sukses

- `POST /api/v1/ml/forecast/demand`
  - Request:
    ```json
    {
      "horizonDays": 7,
      "recentMenuOrders": [
        { "date": "2026-11-20", "menuId": "menu_01", "portions": 80 },
        { "date": "2026-11-20", "menuId": "menu_02", "portions": 40 },
        { "date": "2026-11-21", "menuId": "menu_01", "portions": 100 }
      ]
    }
    ```
  - Response `200 OK`:
    ```json
    {
      "data": {
        "modelName": "RandomForestDemandRegressor",
        "modelVersion": "1.0.0",
        "isSyntheticTrained": true,
        "dataDisclaimer": "Estimasi berbasis data simulasi/terbatas untuk dukungan perencanaan, bukan jaminan operasional.",
        "menuTotals": [
          { "menuId": "menu_01", "totalPredictedPortions": 560 },
          { "menuId": "menu_02", "totalPredictedPortions": 210 }
        ],
        "dailyForecast": [
          { "date": "2026-11-22", "menuId": "menu_01", "predictedPortions": 85 },
          { "date": "2026-11-22", "menuId": "menu_02", "predictedPortions": 30 }
        ]
      },
      "meta": { "requestId": "0192f0c8-7b3a-7000-8000-000000000008" }
    }
    ```

#### Standar Error RFC 9457 (`Content-Type: application/problem+json`)

- `401 Unauthorized`, `404 Not Found` (artefak model belum tersedia), `422 Unprocessable Content` (`horizonDays` di luar `1..30`, riwayat kosong/terlalu sedikit, format tanggal tidak valid), `500 Internal Server Error`, `503 Service Unavailable`.

### Acceptance Criteria

- [ ] Kedua endpoint (`/api/v1/ml/forecast/demand` & `/metadata`) terimplementasi sesuai kontrak OpenAPI 3.1.0 di Scalar `/docs` dan terproteksi `X-Internal-Token`.
- [ ] Endpoint mengembalikan prediksi permintaan **per menu** (`menuTotals` & `dailyForecast`) dalam envelope `{ data, meta }` dengan seluruh nilai porsi `>= 0`.
- [ ] Pengujian data kosong atau terlalu sedikit mengembalikan pesan error/peringatan yang jelas (`422` RFC 9457) tanpa crash.
- [ ] Respons dan metadata secara eksplisit mencantumkan model terpilih dari `DS-04`, status `isSyntheticTrained`, dan pernyataan batas data.
- [ ] Unit test & ASGI test Pytest pada `apps/ai-service/app/ml/forecasting`, linting Ruff, dan typecheck Mypy lulus 100%.

### Keputusan yang Membutuhkan Konfirmasi (PIC / Tim)

- `[Perlu Konfirmasi Tim]` Jumlah minimal hari historis agar inferensi lag/rolling valid (misal minimal 7 hari) dan kesepakatan struktur field `menuId` antara Express (`FS-08`) dan FastAPI (`DS-05`).
- `[Perlu Konfirmasi Tim]` Konfirmasi pemasangan extras `ml` (`uv sync --extra ml`) pada image Docker `ai-service.Dockerfile` (`OPS-02`).

### DoD

- [ ] Modul `apps/ai-service/app/ml/forecasting/` terintegrasi rapi ke `app/main.py` / `app/routers.py`.
- [ ] Pytest, Ruff, dan Mypy lulus tanpa error.
- [ ] Endpoint tampil di OpenAPI 3.1.0 Scalar `/docs` dan terverifikasi terhubung dari `FS-08`.

### Dependencies

- **Prasyarat:** `DS-04` (Artefak Model Terpilih & Metadata Evaluasi), `AI-01` (Kerangka Serving FastAPI).
- **Terkait:** Dikonsumsi oleh `FS-08` (Dasbor Analitik & penggabungan resep `FS-04` untuk estimasi kebutuhan bahan baku).

---

## [DS-06] Verifikasi Implementasi KPI Dasbor & Audit Akurasi Data Akhir

- **Labels:** `area:ds`, `priority:P1-mvp`, `quest:main`, `quest:side`
- **Priority:** `P1-mvp`
- **Klasifikasi Project Plan:** Wajib (Validasi Data, Audit Integritas & Dokumentasi Hasil Uji Akhir M4)
- **Milestone:** `M4: Validasi & Finalisasi (12–20 Des 2026)`
- **Penanggung Jawab (Project Plan):** Chaviela Nazwa Syaqiba, Rio Andika Andriansyah
- **Target Path:** `notebooks`, `data`, `README.md`

### Context

Formula KPI Dasbor telah didefinisikan dan dikunci pada `DS-02` (M2) sebelum implementasi `FS-08` (M3). Memasuki fase validasi akhir (M4), tim Data Science bertugas melakukan **verifikasi kesesuaian implementasi KPI dasbor terhadap definisi `DS-02`**, memeriksa konsistensi estimasi bahan baku hasil forecasting (`DS-05` + `FS-04`), memverifikasi kecocokan angka pada laporan `AI-06`, memastikan seluruh data sintetis tertanda `is_synthetic = true`, serta melakukan audit privasi terakhir agar tidak ada PII pelanggan, data gaji, maupun file mentah `data/raw/*` yang tertinggal di repositori sebelum demonstrasi akhir.

### Scope

**Requirement Wajib (Project Plan):**

- **Verifikasi Implementasi KPI Dasbor:** mencocokkan angka keluaran endpoint `GET /api/v1/analytics/overview` (`FS-08`) terhadap perhitungan independen di Python menggunakan formula terkunci dari `DS-02` (toleransi selisih 0% untuk hitungan total pesanan, porsi, revenue, dan rasio pelunasan).
- **Audit Estimasi Bahan Baku & Output Model:** memverifikasi kesesuaian kalkulasi bahan baku 10/50/100 porsi (`FS-04`), integrasi prediksi per menu (`DS-05` + `FS-08`), ringkasan sentimen (`AI-03`), dan akurasi angka pada narasi `AI-06`.
- **Audit Anonimisasi & Pelabelan Data Sintetis:** memastikan 100% data buatan tertanda `is_synthetic = true` (tidak diklaim sebagai data/feedback nyata) dan 0 kebocoran PII pelanggan atau data gaji di seluruh repositori & data demo.
- **Dokumentasi Hasil Uji & Evaluasi di README + Spreadsheet Pengujian:** memastikan kualitas dataset, distribusi kelas, hasil evaluasi model (Moving Average vs Random Forest, fitur lag/rolling, tuning), dan temuan audit tercatat rapi di README dan Spreadsheet pengujian bersama.

**Rekomendasi Teknis / Implementasi:**

- Jalankan skrip verifikasi silang otomatis (Python script) yang menarik snapshot data uji dari database lokal/staging dan membandingkannya dengan respons JSON `/api/v1/analytics/overview`.

**Out-of-Scope:**

- Merombak definisi formula KPI di M4 (sudah dikunci di `DS-02` M2; M4 hanya perbaikan bug dan audit pasca feature freeze).
- Menambahkan fitur analitik baru di luar cakupan feature freeze akhir M3.

### Business Rules

- Setiap ketidaksesuaian angka antara database/Python dan dasbor web wajib dicatat sebagai bug di GitHub Issues dan diperbaiki sebelum demonstrasi PIC.
- Tidak boleh ada klaim dampak bisnis komersial atau klaim akurasi operasional penuh pada dokumen hasil evaluasi.
- Audit privasi wajib menyatakan 0 temuan PII riil, 0 data gaji, dan 0 file `data/raw/*` di repositori.

### API Contract

Tidak berlaku (tugas audit & verifikasi non-API). Menghasilkan catatan audit akurasi data akhir, pembaruan bagian evaluasi DS pada README, dan pengisian log uji di Spreadsheet bersama.

### Acceptance Criteria

- [ ] Angka KPI pada dasbor web (`FS-08`) terbukti **cocok 100%** dengan perhitungan independen Python berdasarkan formula terkunci dari `DS-02`.
- [ ] Estimasi kebutuhan bahan baku dari forecasting per menu (`DS-05` + `FS-04`) dan angka pada sampel laporan `AI-06` lolos verifikasi silang tanpa selisih angka.
- [ ] 100% data sintetis pada database demo, file CSV/JSON, dan tampilan UI tertanda jelas sebagai `is_synthetic = true` / simulasi.
- [ ] Audit repositori membuktikan 0 kebocoran PII pelanggan riil, 0 data gaji, 0 berkas `data/raw/*`, dan bebas file checkpoint notebook sampah.
- [ ] Ringkasan kualitas dataset, perbandingan model forecasting, dan hasil uji tercatat lengkap di README dan Spreadsheet pengujian bersama.

### Keputusan yang Membutuhkan Konfirmasi (PIC / Tim)

- `[Menunggu Konfirmasi PIC]` Verifikasi akhir kesesuaian data demo dan laporan analitik yang akan ditampilkan saat demonstrasi skenario 100 nasi box.
- `[Perlu Konfirmasi Tim]` Tanda terima hasil verifikasi silang angka analitik antara tim Data Science, Full-Stack, dan AI Engineering sebelum finalisasi presentasi.

### DoD

- [ ] Laporan audit akurasi data & privasi akhir selesai dan seluruh bug temuan telah ditutup.
- [ ] Bagian evaluasi Data Science di README dan Spreadsheet pengujian telah dilengkapi.
- [ ] Repositori bersih dari file sementara dan artefak lokal tak terpakai.

### Dependencies

- **Prasyarat:** `DS-02` (Definisi KPI Terkunci), `DS-04` & `DS-05` (Forecasting), `FS-04`, `FS-05`, `FS-06`, `FS-08` (Dasbor Analitik), `AI-03` (Sentimen), `AI-06` (AI Business Insight).
- **Terkait:** Menjadi gerbang validasi data menjelang demonstrasi akhir pada `FS-09`.
