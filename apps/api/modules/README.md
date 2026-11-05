# Modul Domain API (`apps/api/modules`)

Direktori ini menyimpan batas modul domain backend **Smart Catering**:

- `auth/` — Autentikasi, otorisasi, dan manajemen sesi pengguna.
- `orders/` — Siklus pemesanan katering, jadwal pengiriman, dan status pesanan.
- `inventory/` — Stok bahan baku, pemakaian dapur, dan peringatan ketersediaan.
- `finance/` — Pencatatan pembayaran, arus kas pesanan, dan rekapitulasi keuangan.
  Batas kapabilitas AI (`rag/` dan `ml/`) berada pada layanan Python `apps/ai-service`.

## Status Fase 0

Seluruh subdirektori modul pada Fase 0 adalah **skeleton struktural** (tanpa route bisnis, service palsu, atau query database). Implementasi domain akan ditambahkan pada fase pengembangan berikutnya.
