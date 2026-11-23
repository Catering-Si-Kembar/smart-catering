# Konfigurasi Inference Modal GPU (`infra/modal`)

Batas direktori untuk skrip dan konfigurasi deployment server inference SLM/vLLM open-source pada Modal GPU yang dipanggil secara terpisah melalui HTTP oleh `apps/ai-service`.

**Boundary:** Tidak menyimpan API key atau token akun Modal di repositori; seluruh kredensial diatur melalui secret environment.
