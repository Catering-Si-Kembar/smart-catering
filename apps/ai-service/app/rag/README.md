# Modul `rag` (`apps/ai-service/app/rag`)

Batas modul untuk alur Retrieval-Augmented Generation (pencarian konteks menu, FAQ, dan penyusunan jawaban berbasis pengetahuan internal katering) yang dimiliki oleh layanan Python AI (`@smart-catering/ai-service`).

## Dependensi Opsional

Paket RAG dideklarasikan sebagai extra opsional `rag` pada `apps/ai-service/pyproject.toml`:

- `langchain==1.4.8`
- `chromadb==1.5.9`

**Status Fase 0:** Hanya dokumentasi batas arsitektur. Paket extra `rag` belum diimpor, diinisialisasi, atau diaktifkan pada runtime default Fase 0.
