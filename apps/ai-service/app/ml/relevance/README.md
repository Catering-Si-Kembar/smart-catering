# Sub-modul `relevance` (`apps/ai-service/app/ml/relevance`)

Modul klasifikasi relevansi pertanyaan dua kelas (`relevant` vs `out_of_domain`) untuk menyaring pertanyaan di luar domain katering (Catering Si Kembar) sebelum diteruskan ke alur chatbot dan agen.

## Struktur File

```
apps/ai-service/app/ml/relevance/
├── __init__.py                # Export modul utama (service, preprocess, error)
├── preprocess.py              # Normalisasi teks & singkatan bahasa Indonesia
├── train.py                   # Pembangkit dataset, training scikit-learn, tuning, ekspor artefak & notebook
├── inference.py               # Runtime inference dual-artifact (joblib / pure-Python weights)
├── README.md                  # Dokumentasi teknis modul
└── artifacts/                 # Direktori artefak model (joblib git-ignored)
    ├── relevance_model.joblib          # Scikit-learn pipeline (.joblib)
    ├── relevance_model_weights.json    # Bobot matematis portable untuk CI minimal
    └── relevance_metadata.json         # Metadata evaluasi holdout & perbandingan model
```

## Cara Menjalankan Training

Dari direktori `apps/ai-service/`:

```bash
uv run --no-sync python -m app.ml.relevance.train
```

Proses ini mengeksekusi tahapan:

1. Pembangkitan dataset sintetis reproducible di `data/synthetic/relevance_dataset.csv` dengan label `is_synthetic=true` dan pembagian train/test terstratifikasi 80:20 tanpa kebocoran data (_zero leakage_).
2. Pelatihan dan perbandingan model `MultinomialNB` dan `LogisticRegression`.
3. Hyperparameter tuning menggunakan `GridSearchCV` 5-fold Stratified CV.
4. Ekspor dual-artifact (`relevance_model.joblib`, `relevance_model_weights.json`, dan `relevance_metadata.json`).
5. Pembuatan dan eksekusi notebook eksperimen di `notebooks/04_relevance_classification.ipynb`.

## Dual-Artifact Strategy

Untuk mendukung kompatibilitas deployment di berbagai lingkungan:

1. **Pipeline Joblib (`relevance_model.joblib`)**:
   Memuat pipeline scikit-learn lengkap (`TfidfVectorizer` + `LogisticRegression`). Digunakan saat environment memiliki dependensi ML (`--extra ml`).
2. **Bobot Portabel JSON (`relevance_model_weights.json`)**:
   Menyimpan representasi matematis TF-IDF (`vocabulary`, `idf`, `ngram_range`, `sublinear_tf`) dan koefisien regresi logistik (`coef`, `intercept`). Memungkinkan inferensi _zero-dependency_ pure Python di CI minimal dengan paritas probabilitas identik (`< 1e-3`).
3. **Metadata Evaluasi (`relevance_metadata.json`)**:
   Mencatat riwayat metrik holdout test set (F1-score, presisi, recall, akurasi), matriks konfusi, perbandingan performa baseline versus tuned, dan informasi versi model.

## Ringkasan Metrik Evaluasi

- **Algoritma Terpilih**: `LogisticRegression (tuned)` dengan `class_weight='balanced'`
- **Ukuran Dataset Sintetis**: `439` sampel (`351` train, `88` test) dengan label `is_synthetic=true`
- **Holdout Test Set F1-score**: `0.9735` (ambang batas target `>= 0.88`)
- **Holdout Test Set Akurasi**: `0.9659` (ambang batas target `>= 0.88`)
- **Holdout Test Set Presisi**: `0.9483`
- **Holdout Test Set Recall**: `1.0000`
- **Rata-rata Latensi Inferensi**: `1.493 ms` (ambang batas target `< 100 ms`)
- **Confusion Matrix (Holdout)**: `[[55, 0], [3, 30]]` (labels: `relevant`, `out_of_domain`)
- **Target Kelas**: `relevant` (domain katering) dan `out_of_domain` (luar katering)
