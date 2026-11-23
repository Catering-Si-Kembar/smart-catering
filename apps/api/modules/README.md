# Modul Domain API (`apps/api/modules`)

Direktori ini menyimpan batas modul domain backend **Smart Catering**:

- `auth/` — Autentikasi, otorisasi, dan manajemen sesi pengguna.
- `menus/` — Katalog menu, bahan baku, resep standar terkonfirmasi UMKM, dan kalkulasi kebutuhan bahan berdasarkan jumlah porsi.
- `orders/` — Siklus pemesanan katering, jadwal pengiriman, dan status pesanan.
- `finance/` — Pencatatan pembayaran (DP dan pelunasan), invoice digital, arus kas pesanan, dan rekapitulasi keuangan.
- `analytics/` — Agregasi KPI dasbor analitik, validasi unggahan file data, serta orkestrasi ke layanan forecasting, sentimen, dan AI Business Insight.
- `chat/` — Riwayat percakapan PostgreSQL, otorisasi peran di backend, data baca-saja untuk tools, dan delegasi ke `apps/ai-service`.
- `reminders/` — Jadwal pengingat pesanan, pembayaran, ringkasan keuangan, serta pencatatan status pengiriman idempotent.
  Batas kapabilitas AI (`rag/`, `insight/`, dan `ml/`) berada pada layanan Python `apps/ai-service`.

## Status Fase 0

Seluruh subdirektori modul pada Fase 0 adalah **skeleton struktural** (tanpa route bisnis, service palsu, atau query database). Implementasi domain akan ditambahkan pada fase pengembangan berikutnya.
