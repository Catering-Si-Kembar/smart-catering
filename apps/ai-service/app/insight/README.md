# Modul `insight` (`apps/ai-service/app/insight`)

Batas modul integrasi klien inference SLM/LLM open-source (Modal GPU / vLLM) untuk menghasilkan ringkasan AI Business Insight berbasis data laporan terverifikasi.

**Boundary:** Pemanggilan model inference berjalan melalui klien HTTP terisolasi dengan pencatatan latensi dan penanganan fallback jika layanan inference tidak tersedia.
