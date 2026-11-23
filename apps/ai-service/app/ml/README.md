# Modul `ml` (`apps/ai-service/app/ml`)

Batas modul untuk fitur machine learning yang dimiliki oleh layanan Python AI (`@smart-catering/ai-service`), dibagi menjadi tiga sub-boundary:

- `relevance/` — Klasifikasi relevansi pertanyaan dua kelas sebelum masuk ke alur chatbot.
- `forecasting/` — Estimasi permintaan menu dan kebutuhan bahan baku (baseline Moving Average dan Random Forest).
- `sentiment/` — Klasifikasi sentimen feedback pelanggan (positif/negatif) untuk dasbor analitik.

## Dependensi Opsional

Paket ML dideklarasikan sebagai extra opsional `ml` pada `apps/ai-service/pyproject.toml`:

- `scikit-learn==1.9.1`

**Status Fase 0:** Hanya dokumentasi batas arsitektur. Paket extra `ml` belum diimpor dan belum ada pipeline training maupun inference aktif pada Fase 0.
