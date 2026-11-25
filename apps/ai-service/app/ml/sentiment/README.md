# Sub-modul `sentiment` (`apps/ai-service/app/ml/sentiment`)

Modul Machine Learning untuk klasifikasi sentimen feedback pelanggan Catering Si Kembar (`AI-03` /
Issue `#18`, M2 Side Quest).

## 1. Struktur Modul

- `preprocess.py`: Utilitas normalisasi teks dan tokenisasi bahasa Indonesia (deterministic &
  idempotent, ekspansi singkatan ulasan chat seperti `bgt` → `sangat`, `ga`/`gak` → `tidak`, dll.).
- `train.py`: Pipeline pelatihan scikit-learn, generator dataset sintetis, penanganan _class
  imbalance_, hyperparameter tuning (`GridSearchCV` 5-fold `StratifiedKFold`), pencatatan _error
  analysis_, dan generator notebook eksperimen.
- `inference.py`: `SentimentClassifierService` dengan dukungan _dual-artifact_ (Pipeline lokal
  `.joblib` dan fallback _pure-Python_ `.json`), verifikasi ambang batas `needsAttention >= 0.75`,
  serta inferensi batch (maks. 100 item).
- `artifacts/`:
  - `sentiment_model.joblib`: Pipeline scikit-learn penuh (`TfidfVectorizer` + `LogisticRegression`).
  - `sentiment_model_weights.json`: Bobot matematis model pemenang untuk inferensi CI minimal tanpa
    dependensi ML tambahan.
  - `sentiment_metadata.json`: Metrik evaluasi holdout, perbandingan model, confusion matrix, dan
    analisis error.

## 2. Cara Pelatihan Ulang (Re-Train)

Jalankan perintah berikut dari direktori `apps/ai-service`:

```bash
uv run --no-sync python -m app.ml.sentiment.train
```

Perintah di atas akan:

1. Memperbarui dataset ulasan di `data/synthetic/sentiment_dataset.csv`.
2. Melatih dan membandingkan model `MultinomialNB` vs `LogisticRegression`.
3. Menjalankan hyperparameter tuning 5-fold Stratified CV.
4. Mengekspor ketiga artefak di folder `artifacts/`.
5. Menghasilkan notebook eksperimen tereksekusi di `notebooks/05_sentiment_analysis.ipynb`.

## 3. Hasil Evaluasi Model Aktual (Holdout Test Set 80:20)

- **Dataset:** 420 ulasan unik (`is_synthetic=true`), distribusi realistis: 260 positif (61.9%) dan
  160 negatif (38.1%), mencakup 20 ulasan bernada campuran (_mixed sentiment_).
- **Akurasi:** 97.62% (`0.9762`)
- **F1-Score (Keluhan/Negative):** 96.77% (`0.9677`)
- **Precision:** 100.0% (`1.0000`)
- **Recall:** 93.75% (`0.9375`)
- **Rata-rata Latensi Inferensi:** 2.478 ms (jauh di bawah SLA target < 50 ms).

### Perbandingan Model

| Model                         | Holdout F1 | Holdout Accuracy | Catatan                                           |
| ----------------------------- | ---------- | ---------------- | ------------------------------------------------- |
| MultinomialNB (Baseline)      | 0.9841     | 0.9881           | Baseline Naive Bayes dengan TF-IDF unigram        |
| LogisticRegression (Baseline) | 0.9508     | 0.9643           | C=1.0, TF-IDF unigram, tanpa sublinear TF         |
| LogisticRegression (Tuned)    | 0.9677     | 0.9762           | C=2.0, TF-IDF unigram + bigram, class_weight=None |

#### Alasan Pemilihan Model & Kalibrasi Probabilitas

Meskipun `MultinomialNB` memperoleh F1 baseline sedikit lebih tinggi pada holdout data sintetis (`0.9841` vs `0.9508`), `LogisticRegression (tuned)` (`F1 0.9677`, `Accuracy 0.9762`) dipilih untuk lingkungan produksi karena menghasilkan kalibrasi probabilitas (`predict_proba`) yang jauh lebih stabil dan reliable. Kalibrasi probabilitas yang konsisten sangat penting untuk penentuan ambang batas prioritas komplain operasional `needsAttention >= 0.75`.

## 4. Error Analysis & Mixed Sentiment

- **Ulasan Campuran (_Mixed Sentiment_):** Model 2 kelas mengklasifikasikan sentimen berdasarkan
  bobot leksikal terkuat. Pada ulasan yang memuji rasa tetapi mengeluhkan keterlambatan atau kemasan
  penyok, model mendeteksi keluhan tersebut sebagai sinyal penting.
- **Indikator Prioritas (`needsAttention`):** Ditetapkan aktif (`true`) apabila sentimen bernilai
  `negative` dengan tingkat keyakinan skor `>= 0.75`, berguna untuk menyaring komplain darurat yang
  harus segera ditangani admin di Dasbor Analitik `FS-08`.

## 5. Kepatuhan Asah 2026

- Model dibangun mandiri menggunakan algoritma `scikit-learn` konvensional (TF-IDF +
  LogisticRegression).
- Tidak menggunakan AutoML, TensorFlow Hub, model pretrained HuggingFace, maupun API LLM berbayar.
- Seluruh data sintetis diberi label eksplisit `is_synthetic=true` tanpa data pribadi pelanggan (PII).
