# Sub-modul `relevance` (`apps/ai-service/app/ml/relevance`)

Batas modul klasifikasi relevansi pertanyaan dua kelas untuk menyaring pertanyaan di luar konteks Catering Si Kembar sebelum masuk ke alur chatbot.

**Boundary:** Artefak model dan evaluasi perbandingan dua kandidat model disimpan terpisah dari kode runtime; layanan hanya memuat model tervalidasi untuk inference.
